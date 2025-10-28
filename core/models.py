import csv
import json
import os
import logging
from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import IntegrityError, models
from django.db.models import Case, IntegerField, Value, When
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import ClusterableModel
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core import choices
from core.forms import CoreAdminModelForm
from core.utils.utils import language_iso

User = get_user_model()


class CommonControlField(models.Model):
    """
    Class with common control fields.

    Fields:
        created: Date time when the record was created
        updated: Date time with the last update date
        creator: The creator of the record
        updated_by: Store the last updator of the record
    """

    # Creation date
    created = models.DateTimeField(verbose_name=_("Creation date"), auto_now_add=True)

    # Update date
    updated = models.DateTimeField(verbose_name=_("Last update date"), auto_now=True)

    # Creator user
    creator = models.ForeignKey(
        User,
        verbose_name=_("Creator"),
        related_name="%(class)s_creator",
        editable=False,
        on_delete=models.SET_NULL,
        null=True,
    )

    # Last modifier user
    updated_by = models.ForeignKey(
        User,
        verbose_name=_("Updater"),
        related_name="%(class)s_last_mod_user",
        editable=False,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        abstract = True


class Gender(CommonControlField):
    """
    Class of gender

    Fields:
        sex: physical state of being either male, female, or intersex
    """

    code = models.CharField(_("Code"), max_length=5, null=True, blank=True)

    gender = models.CharField(_("Sex"), max_length=50, null=True, blank=True)

    autocomplete_search_filter = "code"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("code"),
        FieldPanel("gender"),
    ]

    class Meta:
        unique_together = [("code", "gender")]

    def __unicode__(self):
        return self.gender or self.code

    def __str__(self):
        return self.gender or self.code

    @classmethod
    def load(cls, user):
        for item in choices.GENDER_CHOICES:
            code, value = item
            cls.create_or_update(user, code=code, gender=value)

    @classmethod
    def _get(cls, code=None, gender=None):
        try:
            return cls.objects.get(code=code, gender=gender)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(code=code, gender=gender).first()

    @classmethod
    def _create(cls, user, code=None, gender=None):
        try:
            obj = cls()
            obj.gender = gender
            obj.code = code
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls._get(code, gender)

    @classmethod
    def create_or_update(cls, user, code, gender=None):
        try:
            return cls._get(code, gender)
        except cls.DoesNotExist:
            return cls._create(user, code, gender)


class Language(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        code2
    """

    name = models.TextField(_("Language Name"), blank=True, null=True)
    code2 = models.TextField(_("Language code 2"), blank=True, null=True)

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")
        indexes = [
            models.Index(
                fields=[
                    "code2",
                ]
            ),
            models.Index(
                fields=[
                    "name",
                ]
            ),
        ]

    def __unicode__(self):
        if self.name or self.code2:
            return f"{self.name} | {self.code2}"
        return "None"

    def __str__(self):
        if self.name or self.code2:
            return f"{self.name} | {self.code2}"
        return "None"

    @classmethod
    def load(cls, user):
        if cls.objects.count() == 0:
            for k, v in choices.LANGUAGE:
                cls.get_or_create(name=v, code2=k, creator=user)

    @staticmethod
    def get_instance(language):
        if not language:
            return
        if isinstance(language, Language):
            return language
        return Language.get(language)

    @classmethod
    def get_or_create(cls, name=None, code2=None, creator=None):
        code2 = language_iso(code2)
        if code2:
            try:
                return cls.objects.get(code2=code2)
            except cls.DoesNotExist:
                pass

        if name:
            try:
                return cls.objects.get(name=name)
            except cls.DoesNotExist:
                pass

        if name or code2:
            obj = Language()
            obj.name = name
            obj.code2 = code2 or ""
            obj.creator = creator
            obj.save()
            return obj

    @classmethod
    def get(cls, code2):
        if not code2:
            raise ValueError("Language.get requires params: code2")
        try:
            return cls.objects.get(code2=code2)
        except cls.DoesNotExist:
            return cls.objects.get(code2=language_iso(code2))


class TextWithLang(models.Model):
    text = models.TextField(_("Text"), null=True, blank=True)
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        verbose_name=_("Language"),
        null=True,
        blank=True,
    )

    panels = [FieldPanel("text"), AutocompletePanel("language")]

    class Meta:
        abstract = True


class TextLanguageMixin(models.Model):
    rich_text = RichTextField(_("Rich Text"), null=True, blank=True)
    plain_text = models.TextField(_("Plain Text"), null=True, blank=True)
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        verbose_name=_("Language"),
        null=True,
        blank=True,
    )

    panels = [
        AutocompletePanel("language"),
        FieldPanel("rich_text"),
        FieldPanel("plain_text"),
    ]

    class Meta:
        abstract = True


class LanguageFallbackManager(models.Manager):
    def get_object_in_preferred_language(self, language):
        mission = self.filter(language=language)
        if mission:
            return mission

        language_order = ["pt", "es", "en"]
        langs = self.all().values_list("language", flat=True)
        languages = Language.objects.filter(id__in=langs)

        # Define a ordem baseado na lista language_order
        order = [
            When(code2=lang, then=Value(i)) for i, lang in enumerate(language_order)
        ]
        ordered_languages = languages.annotate(
            language_order=Case(
                *order, default=Value(len(language_order)), output_field=IntegerField()
            )
        ).order_by("language_order")

        for lang in ordered_languages:
            mission = self.filter(language=lang)
            if mission:
                return mission
        return None


class RichTextWithLanguage(models.Model):
    rich_text = RichTextField(_("Rich Text"), null=True, blank=True)
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        verbose_name=_("Language"),
        null=True,
        blank=True,
    )

    panels = [
        AutocompletePanel("language"),
        FieldPanel("rich_text"),
    ]

    @property
    def get_text_pure(self):
        return strip_tags(self.rich_text)

    objects = LanguageFallbackManager()

    class Meta:
        abstract = True


class FlexibleDate(models.Model):
    year = models.IntegerField(_("Year"), null=True, blank=True)
    month = models.IntegerField(_("Month"), null=True, blank=True)
    day = models.IntegerField(_("Day"), null=True, blank=True)

    def __unicode__(self):
        return "%s/%s/%s" % (self.year, self.month, self.day)

    def __str__(self):
        return "%s/%s/%s" % (self.year, self.month, self.day)

    @property
    def data(self):
        return dict(
            date__year=self.year,
            date__month=self.month,
            date__day=self.day,
        )


class License(CommonControlField):
    license_type = models.CharField(max_length=255, null=True, blank=True)

    autocomplete_search_field = "license_type"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("license_type"),
    ]

    class Meta:
        unique_together = [("license_type",)]
        verbose_name = _("License")
        verbose_name_plural = _("Licenses")
        indexes = [
            models.Index(
                fields=[
                    "license_type",
                ]
            ),
        ]

    def __unicode__(self):
        return self.license_type or ""

    def __str__(self):
        return self.license_type or ""

    @classmethod
    def load(cls, user):
        for license_type, v in choices.LICENSE_TYPES:
            cls.create_or_update(user, license_type)

    @classmethod
    def get(
        cls,
        license_type,
    ):
        if not license_type:
            raise ValueError("License.get requires license_type parameters")
        filters = dict(license_type__iexact=license_type)
        try:
            return cls.objects.get(**filters)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**filters).first()

    @classmethod
    def create(
        cls,
        user,
        license_type=None,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.license_type = license_type or obj.license_type
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(license_type=license_type)

    @classmethod
    def create_or_update(
        cls,
        user,
        license_type=None,
    ):
        try:
            return cls.get(license_type=license_type)
        except cls.DoesNotExist:
            return cls.create(user, license_type)


class LicenseStatement(CommonControlField):
    url = models.CharField(max_length=255, null=True, blank=True)
    license_p = RichTextField(null=True, blank=True)
    language = models.ForeignKey(
        Language, on_delete=models.SET_NULL, null=True, blank=True
    )
    license = models.ForeignKey(
        License, on_delete=models.SET_NULL, null=True, blank=True
    )

    panels = [
        FieldPanel("url"),
        FieldPanel("license_p"),
        AutocompletePanel("language"),
        AutocompletePanel("license"),
    ]

    autocomplete_search_field = "license_p"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.language} {self.license_p}"

    class Meta:
        unique_together = [("url", "license_p", "language")]
        verbose_name = _("License")
        verbose_name_plural = _("Licenses")
        indexes = [
            models.Index(
                fields=[
                    "url",
                ]
            ),
        ]

    def __unicode__(self):
        return self.url or ""

    def __str__(self):
        return self.url or ""

    @classmethod
    def get(
        cls,
        url=None,
        license_p=None,
        language=None,
    ):
        if not url and not license_p:
            raise ValueError("LicenseStatement.get requires url or license_p")
        try:
            return cls.objects.get(
                url__iexact=url, license_p__iexact=license_p, language=language
            )
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(
                url__iexact=url, license_p__iexact=license_p, language=language
            ).first()

    @classmethod
    def create(
        cls,
        user,
        url=None,
        license_p=None,
        language=None,
        license=None,
    ):
        if not url and not license_p:
            raise ValueError("LicenseStatement.create requires url or license_p")
        try:
            obj = cls()
            obj.creator = user
            obj.url = url or obj.url
            obj.license_p = license_p or obj.license_p
            obj.language = language or obj.language
            # instance of License
            obj.license = license or obj.license
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(url, license_p, language)

    @classmethod
    def create_or_update(
        cls,
        user,
        url=None,
        license_p=None,
        language=None,
        license=None,
    ):
        try:
            data = dict(
                url=url, license_p=license_p, language=language and language.code2
            )
            try:
                obj = cls.get(url, license_p, language)
                obj.updated_by = user
                obj.url = url or obj.url
                obj.license_p = license_p or obj.license_p
                obj.language = language or obj.language
                # instance of License
                obj.license = license or obj.license
                obj.save()
                return obj
            except cls.DoesNotExist:
                return cls.create(user, url, license_p, language, license)
        except Exception as e:
            raise ValueError(
                f"Unable to create or update LicenseStatement for {data}: {type(e)} {e}"
            )

    @staticmethod
    def parse_url(url):
        license_type = None
        license_version = None
        license_language = None

        url = url.lower()
        url_parts = url.split("/")
        if not url_parts:
            return {}

        license_types = dict(choices.LICENSE_TYPES)
        for lic_type in license_types.keys():
            if lic_type in url_parts:
                license_type = lic_type

                try:
                    version = url.split(f"/{license_type}/")
                    version = version[-1].split("/")[0]
                    isdigit = False
                    for c in version.split("."):
                        if c.isdigit():
                            isdigit = True
                            continue
                        else:
                            isdigit = False
                            break
                    if isdigit:
                        license_version = version
                except (AttributeError, TypeError, ValueError):
                    pass
                break

        return dict(
            license_type=license_type,
            license_version=license_version,
            license_language=license_language,
        )


class FileWithLang(models.Model):
    file = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("File"),
        help_text="",
        related_name="+",
    )

    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        verbose_name=_("Language"),
        null=True,
        blank=True,
    )

    panels = [
        AutocompletePanel("language"),
        FieldPanel("file"),
    ]

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    class Meta:
        abstract = True


class BaseHistory(models.Model):
    initial_date = models.DateField(_("Initial Date"), null=True, blank=True)
    final_date = models.DateField(_("Final Date"), null=True, blank=True)

    panels = [
        FieldPanel("initial_date"),
        FieldPanel("final_date"),
    ]

    class Meta:
        abstract = True


class BaseLogo(models.Model):
    """
    Model para armazenar diferentes versões de logos da coleção
    com suporte a múltiplos tamanhos e idiomas
    """

    logo = models.ForeignKey(
        "wagtailimages.Image",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
        verbose_name=_("Logo Image"),
    )
    language = models.ForeignKey(
        Language,
        verbose_name=_("Logo language"),
        help_text=_("Language version of this logo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    panels = [
        FieldPanel("logo"),
        FieldPanel("language"),
    ]

    class Meta:
        abstract = True
        ordering = ['sort_order', 'language']

    def __str__(self):
        return f"{self.collection} - {self.language}"


ICON_MAP = {
    "twitter": "icon-twitter",
    "instagram": "icon-instagram",
    "linkedin": "icon-linkedin",
    "github": "icon-github",
    "facebook": "icon-facebook",
    "tiktok": "icon-tiktok",
    "youtube": "icon-youtube",
}


class SocialNetwork(models.Model):
    name = models.CharField(
        _("Name"),
        choices=choices.SOCIAL_NETWORK_NAMES,
        max_length=20,
        null=True,
        blank=True,
    )
    url = models.URLField(_("URL"), null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("url"),
    ]

    class Meta:
        verbose_name = _("Social Network")
        verbose_name_plural = _("Social Networks")
        indexes = [
            models.Index(
                fields=[
                    "url",
                ]
            ),
        ]
        abstract = True

    @property
    def icon_class(self):
        return ICON_MAP.get(self.name, "icon-reload")

    @property
    def data(self):
        """Retorna um dicionário com os dados essenciais da rede social."""
        return {
            "name": self.name,
            "url": self.url,
        }

    def __str__(self):
        return self.name


class ExportDestination(CommonControlField):
    acronym = models.CharField(_("Acronym"), max_length=30, null=True, blank=False)

    panels = [
        FieldPanel("acronym"),
    ]

    base_form_class = CoreAdminModelForm
    autocomplete_search_field = "acronym"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.acronym}"

    class Meta:
        ordering = ["acronym"]

    @classmethod
    def get_or_create(cls, destination_name, user=None):
        """Obtém o destino de exportação."""
        try:
            return cls.objects.get(acronym=destination_name)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(acronym=destination_name).first()
        except cls.DoesNotExist:
            obj = cls()
            obj.acronym = destination_name
            obj.creator = user
            obj.save()
            return obj


class BaseExporter(CommonControlField, ClusterableModel):
    """
    Classe base abstrata para controle de exportações
    """

    pid = models.CharField(
        _("PID"),
        max_length=24,
        db_index=True,
    )
    destination = models.ForeignKey(
        ExportDestination,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Destination"),
    )
    status = models.CharField(
        _("Status"),
        max_length=15,
        null=True,
        blank=True,
        choices=choices.EXPORTATION_STATUS,
        default=choices.EXPORTATION_STATUS_TODO,
    )
    collection = models.ForeignKey(
        "collection.Collection",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Collection"),
    )
    detail = models.JSONField(null=True, blank=True)
    # se preencher, vai gerar histórico, se nunca preencher não mantém histórico
    version = models.CharField(_("Version"), max_length=26, null=True, blank=True)

    def __str__(self):
        return f"{self.parent} {self.destination} {self.updated.isoformat()}"

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["pid", "destination", "collection"]),
        ]

    @classmethod
    def get_panels(cls):
        """
        Retorna os panels do Wagtail para a interface administrativa.
        """
        panels_ids = [
            FieldPanel("pid", read_only=True),
            FieldPanel("collection", read_only=True),
            FieldPanel("destination", read_only=True),
            FieldPanel("created", read_only=True),
            FieldPanel("updated", read_only=True),
        ]

        panels_events = [
            FieldPanel("status", read_only=True),
            FieldPanel("detail", read_only=True),
        ]

        return TabbedInterface(
            [
                ObjectList(panels_ids, heading=_("Identification")),
                ObjectList(panels_events, heading=_("Events")),
            ]
        )

    @classmethod
    def start(cls, user, parent, pid, destination, collection, version=None):
        """
        Marca um objeto como exportado

        Args:
            user: Usuário realizando a exportação
            parent: Objeto pai sendo exportado
            pid: Identificador único do objeto pai
            destination: Destino da exportação
            collection: Coleção
            version: Versão (opcional)
        """
        filter_kwargs = {
            "parent": parent,
            "pid": pid,
            "destination": destination,
            "collection": collection,
            "version": version,
        }

        defaults = {"creator": user}

        obj, created = cls.objects.get_or_create(**filter_kwargs, defaults=defaults)

        if not created:
            obj.updated = datetime.now()
            obj.updated_by = user
        obj.status = choices.EXPORTATION_STATUS_TODO
        obj.save()
        return obj

    def finish(
        self, user, completed, events, response=None, errors=None, exceptions=None
    ):
        """Finaliza uma exportação com status e detalhes"""
        if errors or exceptions:
            completed = False
        else:
            completed = True
        if completed:
            self.status = choices.EXPORTATION_STATUS_DONE
        else:
            self.status = choices.EXPORTATION_STATUS_PENDING

        self.detail = {
            "response": response,
            "events": events,
            "errors": errors,
            "exceptions": exceptions,
        }
        for k, v in self.detail.items():
            try:
                json.dumps(v)
            except Exception as e:
                self.detail[k] = str(v)
        self.updated = datetime.utcnow()
        self.updated_by = user
        self.save()

    @property
    def response(self):
        return (self.detail or {}).get("response")

    @classmethod
    def is_exported(cls, parent, pid, destination, collection):
        """
        Verifica se um objeto já foi exportado

        Args:
            parent: Objeto pai sendo verificado
            pid: Identificador único do objeto pai
            destination: Destino da exportação
            collection: Coleção
        """
        filter_kwargs = {
            "pid": pid,
            "destination": destination,
            "collection": collection,
        }

        last_export = cls.objects.filter(**filter_kwargs).order_by("-updated").first()
        return last_export and last_export.status == choices.EXPORTATION_STATUS_DONE

    @classmethod
    def get_demand(
        cls, user, parent, destination, pid, collection, version=None, force_update=None
    ):
        """
        Exporta um objeto para uma única coleção.

        Args:
            user: Usuário realizando a exportação
            parent: Objeto pai sendo exportado
            destination: Destino da exportação
            pid: Identificador único do objeto pai
            collection: Coleção
            version: Versão, somente se quiser manter histórico
            force_update: Forçar atualização mesmo se já exportado
        """
        if not parent or not destination or not pid or not collection or not user:
            raise ValueError(
                f"{cls}.get_demand requires user ({user}), parent ({parent}), destination ({destination}), pid ({pid}), collection ({collection})"
            )
        if isinstance(destination, str):
            destination = ExportDestination.get_or_create(destination, user)
        if force_update:
            # version = datetime.utcnow().isoformat()
            return cls.start(user, parent, pid, destination, collection, version)
        if not cls.is_exported(parent, pid, destination, collection):
            # version = datetime.utcnow().isoformat()
            return cls.start(user, parent, pid, destination, collection, version)


class BaseLegacyRecord(CommonControlField):
    """
    Modelo que representa a coleta de dados de genérica (para journal, issue e article) na API Article Meta.

    from:
        https://articlemeta.scielo.org/api/v1/journal/?collection={collection}&issn={issn}"
    """
    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("todo", _("To Do")),
        ("done", _("Done")),
    ]
    collection = models.ForeignKey(
        "collection.Collection",
        verbose_name=_("Collection"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    url = models.URLField(
        max_length=300,
        null=True,
        blank=True,
    )
    data = models.JSONField(
        _("JSON File"),
        null=True,
        blank=True,
    )
    processing_date = models.CharField(
        _("Processing Date"),
        max_length=10,
        null=True,
        blank=True,
        help_text=_("Date in YYYY-MM-DD format")
    )
    status = models.CharField(
        _("Status"),
        max_length=10,
        choices=STATUS_CHOICES,
        default="todo",
        null=True,
        blank=True,
    )
    base_form_class = CoreAdminModelForm

    panels = [
        AutocompletePanel("collection"),
        FieldPanel("pid"),
        FieldPanel("status"),
        FieldPanel("processing_date"),
        FieldPanel("url"),
        FieldPanel("data", read_only=True),
    ]
    autocomplete_search_field = "pid"

    def autocomplete_label(self):
        return f"{self.pid} {self.collection}"

    class Meta:
        abstract = True

    def __unicode__(self):
        return f"{self.pid} | {self.collection}"

    def __str__(self):
        return f"{self.pid} | {self.collection}"

    @classmethod
    def get(cls, pid, collection):
        if not pid and not collection:
            raise ValueError("Param pid and collection_acron3 is required")
        return cls.objects.get(pid=pid, collection=collection)

    @classmethod
    def create(cls, pid, collection, data=None, user=None, url=None, processing_date=None, status=None, new_record=None):
        if not pid or not collection or not user:
            raise ValueError(f"{cls.__name__} create requires pid {pid}, collection {collection}, user {user}")
        obj = cls()
        obj.pid = pid
        obj.collection = collection
        if url:
            obj.url = url
        if status:
            obj.status = status
        if data:
            obj.data = data
        if processing_date:
            obj.processing_date = processing_date
        if new_record:
            obj.new_record = new_record
        obj.creator = user
        obj.save()
        return obj
    
    @classmethod
    def create_or_update(cls, pid, collection, data=None, user=None, url=None, status=None, processing_date=None, force_update=None, new_record=None):
        try:
            obj = cls.get(pid=pid, collection=collection)
            obj.updated_by = user
        except cls.DoesNotExist:
            return cls.create(pid, collection, data, user, url=url, processing_date=processing_date, status=status, new_record=new_record)
        except cls.MultipleObjectsReturned:
            obj = cls.objects.filter(pid=pid, collection=collection).order_by("-updated").first()
            obj.updated_by = user

        if processing_date and processing_date == obj.processing_date:
            if not force_update:
                return obj

        if url:
            obj.url = url
        if data:
            obj.data = data
        if status:
            obj.status = status or "todo"
        if processing_date:
            obj.processing_date = processing_date
        if new_record is not None:
            obj.new_record = new_record
        obj.save()
        return obj

    @property
    def legacy_keys(self):
        return {
            "collection_acron3": self.collection.acron3,
            "collection": self.collection,
            "pid": self.pid,
            "source": "migrated" if self.data else "generated",
        }
