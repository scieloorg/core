import csv
import os

from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.db.models import Case, When, Value, IntegerField
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.search import index
from wagtail.snippets.models import register_snippet
from wagtailautocomplete.edit_handlers import AutocompletePanel

from . import choices
from .utils.utils import language_iso

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
        
        language_order = ['pt', 'es', 'en']
        langs = self.all().values_list("language", flat=True)
        languages = Language.objects.filter(id__in=langs)
        
        # Define a ordem baseado na lista language_order
        order = [When(code2=lang, then=Value(i)) for i, lang in enumerate(language_order)]
        ordered_languages = languages.annotate(
            language_order=Case(*order, default=Value(len(language_order)), output_field=IntegerField())
        ).order_by('language_order')


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
        unique_together = [("license_type", )]
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
        filters = dict(
            license_type__iexact=license_type
        )
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
        License, on_delete=models.SET_NULL, null=True, blank=True)

    panels = [
        FieldPanel("url"),
        FieldPanel("license_p"),
        AutocompletePanel("language"),
        AutocompletePanel("license"),
    ]

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
                url__iexact=url, license_p__iexact=license_p, language=language)
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
                url=url,
                license_p=license_p,
                language=language and language.code2
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
            raise ValueError(f"Unable to create or update LicenseStatement for {data}: {type(e)} {e}")

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
        help_text='',
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
