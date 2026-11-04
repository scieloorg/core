import logging
from functools import cached_property

from django import forms
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import (
    BaseHistory,
    BaseLogo,
    CommonControlField,
    Language,
    SocialNetwork,
    TextWithLang,
)
from core.utils.utils import fetch_data
from organization.models import HELP_TEXT_ORGANIZATION, Organization

from collection import choices


class MultipleChoiceArrayField(ArrayField):
    """
    ArrayField cujo formulário apresenta as opções do base_field
    como múltipla escolha (checkboxes), em vez de texto separado por vírgula.
    """

    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.TypedMultipleChoiceField,
            "choices": self.base_field.choices,
            "coerce": self.base_field.to_python,
            "widget": forms.CheckboxSelectMultiple,
        }
        defaults.update(kwargs)
        # Ignora ArrayField.formfield (SimpleArrayField)
        return super(ArrayField, self).formfield(**defaults)


ARTICLEMETA_COLLECTIONS_URL = (
    "https://articlemeta.scielo.org/api/v1/collection/identifiers/"
)

ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY = "collection.ensure_network_classification"
# intervalo mínimo (segundos) entre consultas ao articlemeta feitas por
# Collection.ensure_network_classification
ENSURE_NETWORK_CLASSIFICATION_INTERVAL = 600


def normalize_network_classification(network_classification):
    """
    Retorna network_classification como lista ou None
    Ex.: "scielonetwork" -> ["scielonetwork"]
    """
    if isinstance(network_classification, str):
        network_classification = [network_classification]
    return [item for item in network_classification or [] if item] or None


class CollectionName(TextWithLang):
    collection = ParentalKey(
        "Collection",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="collection_name",
    )

    panels = [
        AutocompletePanel("language"),
        FieldPanel("text"),
    ]

    @property
    def data(self):
        d = {
            "collection_name__text": self.text,
            "collection_name__language": self.language,
        }

        return d

    def __unicode__(self):
        return self.text

    def __str__(self):
        return self.text

    @classmethod
    def get_or_create(cls, collection, lang, name, user=None):
        try:
            obj = cls.objects.get(collection=collection, language=lang, text=name)
        except cls.DoesNotExist:
            obj = cls()
            obj.collection = collection
            obj.language = lang
            obj.text = name
            obj.creator = user
            obj.save()
        return obj


class Collection(CommonControlField, ClusterableModel):
    acron3 = models.CharField(
        _("Acronym with 3 chars"), max_length=10, null=True, blank=True
    )
    acron2 = models.CharField(
        _("Acronym with 2 chars"), max_length=10, null=True, blank=True
    )
    code = models.CharField(_("Code"), max_length=10, null=True, blank=True)
    domain = models.URLField(_("Domain"), null=True, blank=True)
    main_name = models.TextField(_("Main name"), null=True, blank=True)
    status = models.CharField(
        _("Status"), choices=choices.STATUS, max_length=20, null=True, blank=True
    )
    has_analytics = models.BooleanField(_("Has analytics"), null=True, blank=True)
    # Antes era type
    collection_type = models.CharField(
        _("Collection Type"), choices=choices.TYPE, max_length=20, null=True, blank=True
    )
    is_active = models.BooleanField(_("Is active"), null=True, blank=True)
    foundation_date = models.DateField(_("Foundation data"), null=True, blank=True)
    platform_status = models.CharField(
        _("Platform Status"), choices=choices.PLATFORM_STATUS, max_length=20, null=True, blank=True,
    )
    network_classification = MultipleChoiceArrayField(
        models.CharField(
            max_length=20,
            choices=choices.NETWORK_CLASSIFICATION,
        ),
        verbose_name=_("Network classification"),
        null=True,
        blank=True,
    )
    autocomplete_search_field = "main_name"

    def autocomplete_label(self):
        return str(self)

    # Definir as abas separadamente
    identification_panels = [
        FieldPanel("acron3"),
        FieldPanel("acron2"),
        FieldPanel("code"),
        FieldPanel("domain"),
        FieldPanel("main_name"),
        InlinePanel("collection_name", label=_("Translated names")),
    ]

    other_characteristics_panels = [
        FieldPanel("status"),
        FieldPanel("has_analytics"),
        FieldPanel("collection_type"),
        FieldPanel("is_active"),
        FieldPanel("platform_status"),
        FieldPanel("network_classification", widget=forms.CheckboxSelectMultiple),
        FieldPanel("foundation_date"),
    ]

    logo_panels = [
        InlinePanel("logos", label=_("Logos"), min_num=0),
    ]
    supporting_organization_panels = [
        InlinePanel("supporting_organization", label=_("Supporting Organization")),
    ]
    executing_organization_panels = [
        InlinePanel("executing_organization", label=_("Executing Organization")),
    ]

    social_network_panels = [
        InlinePanel("social_network", label=_("Social networks")),
    ]

    # Criar a interface com abas
    edit_handler = TabbedInterface(
        [
            ObjectList(identification_panels, heading=_("Identification")),
            ObjectList(
                other_characteristics_panels, heading=_("Other characteristics")
            ),
            ObjectList(logo_panels, heading=_("Logos")),
            ObjectList(
                supporting_organization_panels, heading=_("Supporting Organizations")
            ),
            ObjectList(
                executing_organization_panels, heading=_("Executing Organization")
            ),
            ObjectList(social_network_panels, heading=_("Social networks")),
        ]
    )

    class Meta:
        verbose_name = _("Collection")
        verbose_name_plural = _("Collections")
        indexes = [
            models.Index(
                fields=[
                    "acron3",
                ]
            ),
            models.Index(
                fields=[
                    "acron2",
                ]
            ),
            models.Index(
                fields=[
                    "code",
                ]
            ),
            models.Index(
                fields=[
                    "domain",
                ]
            ),
            models.Index(
                fields=[
                    "main_name",
                ]
            ),
            models.Index(
                fields=[
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "collection_type",
                ]
            ),
        ]

    @cached_property
    def base_url(self):
        """Retorna o domain pronto para compor URLs, adicionando protocolo se ausente."""
        if self.domain and not self.domain.startswith(("http://", "https://")):
            return f"https://{self.domain}"
        return self.domain

    @property
    def data(self):
        d = {
            "collection__acron3": self.acron3,
            "collection__acron2": self.acron2,
            "collection__code": self.code,
            "collection__domain": self.domain,
            "collection__main_name": self.main_name,
            "collection__status": self.status,
            "collection__has_analytics": self.has_analytics,
            "collection__collection_type": self.collection_type,
            "collection__is_active": self.is_active,
            "collection__foundation_date": self.foundation_date,
            "collection__network_classification": self.network_classification,
        }

        if self.name:
            d.update(self.name.data)

        return d

    def __unicode__(self):
        return f"{self.main_name or self.acron3}"

    def __str__(self):
        return f"{self.main_name or self.acron3}"

    base_form_class = CoreAdminModelForm

    @classmethod
    def load(cls, user, collections_data=None, verify=False):
        if not collections_data:
            collections_data = fetch_data(
                ARTICLEMETA_COLLECTIONS_URL,
                json=True,
                verify=verify,
            )

        for collection_data in collections_data:
            logging.info(collection_data)
            cls.create_or_update(
                user,
                main_name=collection_data.get("original_name"),
                acron2=collection_data.get("acron2"),
                acron3=collection_data.get("acron"),
                code=collection_data.get("code"),
                domain=collection_data.get("domain"),
                names=collection_data.get("name"),
                status=collection_data.get("status"),
                has_analytics=collection_data.get("has_analytics"),
                collection_type=collection_data.get("type"),
                is_active=collection_data.get("is_active"),
                network_classification=collection_data.get("network_classification"),
            )

    @classmethod
    def get_collections_without_network_classification(cls):
        return cls.objects.filter(
            models.Q(network_classification__isnull=True)
            | models.Q(network_classification=[])
        )

    @classmethod
    def ensure_network_classification(cls, user):
        """
        Garante network_classification das coleções antes de seu uso para
        identificar a coleção principal (ex.: PidProviderXML.register de
        artigos publicados em mais de uma coleção).

        Consulta o articlemeta somente se há coleções sem esse dado e, no
        máximo, uma vez a cada ENSURE_NETWORK_CLASSIFICATION_INTERVAL
        segundos, evitando uma consulta por registro quando o articlemeta
        está indisponível ou não tem a coleção.
        Falhas são registradas no log e não interrompem quem chama.
        """
        if not getattr(settings, "COLLECTION_ENSURE_NETWORK_CLASSIFICATION", True):
            return None
        try:
            if not cls.get_collections_without_network_classification().exists():
                return None
            # cache.add é atômico: somente um processo consulta o articlemeta
            if not cache.add(
                ENSURE_NETWORK_CLASSIFICATION_CACHE_KEY,
                True,
                ENSURE_NETWORK_CLASSIFICATION_INTERVAL,
            ):
                return None
            return cls.complete_network_classification(user)
        except Exception as e:
            logging.exception(f"Collection.ensure_network_classification: {e}")
            return None

    @classmethod
    def complete_network_classification(cls, user, collections_data=None, verify=False):
        """
        Preenche em lote network_classification das coleções que estão
        sem esse dado, a partir dos dados do articlemeta.
        Coleções já preenchidas não são alteradas.
        """
        queryset = cls.get_collections_without_network_classification()
        result = {"updated": [], "not_found": []}
        if not queryset.exists():
            return result

        if not collections_data:
            collections_data = fetch_data(
                ARTICLEMETA_COLLECTIONS_URL,
                json=True,
                verify=verify,
            )
        network_classification_by_acron = {
            item.get("acron"): normalize_network_classification(
                item.get("network_classification")
            )
            for item in collections_data
        }

        now = timezone.now()
        items = []
        for obj in queryset:
            network_classification = network_classification_by_acron.get(obj.acron3)
            if not network_classification:
                result["not_found"].append(obj.acron3)
                continue
            obj.network_classification = network_classification
            obj.updated_by = user
            # bulk_update não aplica auto_now
            obj.updated = now
            items.append(obj)
            result["updated"].append(obj.acron3)

        cls.objects.bulk_update(
            items, ["network_classification", "updated_by", "updated"]
        )
        logging.info(f"Collection.complete_network_classification: {result}")
        return result

    @classmethod
    def get(cls, acron3):
        return cls.objects.get(acron3=acron3)

    @classmethod
    def get_national_journal_collections(cls):
        """
        Retorna as coleções do tipo journals cuja classificação de rede
        é exclusivamente scielonetwork
        """
        return cls.objects.filter(
            collection_type="journals",
            network_classification=["scielonetwork"],
        )

    @classmethod
    def create_or_update(
        cls,
        user,
        main_name,
        acron2,
        acron3,
        code,
        domain,
        names,
        status,
        has_analytics,
        collection_type,
        is_active,
        network_classification=None,
    ):
        try:
            obj = cls.objects.get(acron3=acron3)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.acron3 = acron3
            obj.creator = user

        obj.main_name = main_name
        obj.acron2 = acron2
        obj.code = code
        # Adicionar https:// ao domain se não tiver protocolo
        if domain and not domain.startswith(('http://', 'https://')):
            obj.domain = f"https://{domain}"
        else:
            obj.domain = domain
        obj.status = status
        obj.has_analytics = has_analytics
        obj.collection_type = collection_type
        obj.is_active = is_active
        obj.network_classification = normalize_network_classification(
            network_classification
        )
        obj.save()
        for language in names or {}:
            lang = Language.get_or_create(code2=language, creator=user)
            CollectionName.get_or_create(obj, lang, names.get(language), user)
        obj.save()
        logging.info(acron3)
        return obj

    @property
    def name(self):
        """Retorna o primeiro nome da coleção ou None"""
        return self.collection_name.first()

    @property
    def names_list(self):
        """Retorna todos os nomes da coleção"""
        return list(self.collection_name.all())

    def get_name_for_language(self, lang_code=None):
        """
        Retorna o nome da coleção no idioma especificado.
        Se não envontrar, retorna o main_name ou o primeiro disponível.
        """
        from django.utils import translation

        if not lang_code:
            lang_code = translation.get_language()
        name_obj = CollectionName.objects.filter(
            collection=self, language__code2=lang_code
        ).first()
        if name_obj:
            return name_obj.text
        return self.main_name or (
            self.collection_name.first().text if self.collection_name.exists() else ""
        )

    @classmethod
    def get_national_journal_collections(cls):
        """
        Retorna as coleções cuja classificação de rede
        é exclusivamente scielonetwork
        """
        return cls.objects.filter(network_classification=["scielonetwork"])

    @property
    def is_national_journal_collection(self):
        return self.network_classification == ["scielonetwork"]

    @classmethod
    def get_acronyms(cls, collection_acron_list):
        queryset = cls.objects
        if not collection_acron_list:
            return queryset.values_list("acron3", flat=True)
        
        if not isinstance(collection_acron_list, list):
            collection_acron_list = [collection_acron_list]
        return queryset.filter(acron3__in=collection_acron_list).values_list("acron3", flat=True)    


class CollectionSocialNetwork(Orderable, SocialNetwork):
    page = ParentalKey(
        Collection,
        on_delete=models.SET_NULL,
        related_name="social_network",
        null=True,
    )


class CollectionSupportingOrganization(Orderable, ClusterableModel, BaseHistory):
    collection = ParentalKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        related_name="supporting_organization",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=HELP_TEXT_ORGANIZATION,
    )

    panels = BaseHistory.panels + [
        AutocompletePanel("organization"),
    ]

    class Meta:
        verbose_name = _("Supporting Organization")
        verbose_name_plural = _("Supporting Organizations")

    def __str__(self):
        return str(self.organization)


class CollectionExecutingOrganization(Orderable, ClusterableModel, BaseHistory):
    collection = ParentalKey(
        Collection,
        on_delete=models.SET_NULL,
        null=True,
        related_name="executing_organization",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=HELP_TEXT_ORGANIZATION,
    )

    panels = BaseHistory.panels + [
        AutocompletePanel("organization"),
    ]

    class Meta:
        verbose_name = _("Executing Organization")
        verbose_name_plural = _("Executing Organizations")

    def __str__(self):
        return str(self.organization)


class CollectionLogo(Orderable, BaseLogo):
    """
    Model para armazenar diferentes versões de logos da coleção
    com suporte a múltiplos tamanhos e idiomas
    """

    collection = ParentalKey(
        "Collection",
        on_delete=models.CASCADE,
        related_name="logos",
        verbose_name=_("Collection"),
    )

    class Meta:
        verbose_name = _("Collection Logo")
        verbose_name_plural = _("Collection Logos")
        ordering = ["sort_order", "language", "size"]
        unique_together = [
            ("collection", "size", "language"),
        ]

    def __str__(self):
        return f"{self.collection} - {self.language} ({self.size})"
