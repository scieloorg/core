import logging

from django.db import models
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

from . import choices


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
    def load(cls, user, collections_data=None):
        if not collections_data:
            collections_data = fetch_data(
                "https://articlemeta.scielo.org/api/v1/collection/identifiers/",
                json=True,
                verify=False,
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
            )

    @classmethod
    def get(cls, acron3):
        return cls.objects.get(acron3=acron3)

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
        obj.domain = domain
        obj.status = status
        obj.has_analytics = has_analytics
        obj.collection_type = collection_type
        obj.is_active = is_active
        obj.save()
        for language in names:
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
