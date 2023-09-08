from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtailautocomplete.edit_handlers import AutocompletePanel
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from . import choices
from .utils.utils import language_iso

User = get_user_model()


@register_snippet
class Gender(index.Indexed, models.Model):
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

    search_fields = [
        index.SearchField("code", partial_match=True),
        index.SearchField("gender", partial_match=True),
    ]

    def __unicode__(self):
        return self.gender or self.code

    def __str__(self):
        return self.gender or self.code


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


class Language(CommonControlField):
    """
    Represent the list of states

    Fields:
        name
        code2
    """

    name = models.TextField(_("Language Name"), blank=True, null=True)
    code2 = models.TextField(_("Language code 2"), blank=True, null=True)
    
    autocomplete_search_field = "code2"
    
    def autocomplete_label(self):
        return str(self)
    
    class Meta:
        verbose_name = _("Language")
        verbose_name_plural = _("Languages")

    def __unicode__(self):
        return self.code2 or "idioma ausente / não informado"

    def __str__(self):
        return self.code2 or "idioma ausente / não informado"

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

    panels = [
        FieldPanel("text"), 
        AutocompletePanel("language")]

    class Meta:
        abstract = True


class RichTextWithLang(models.Model):
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
    url = models.CharField(max_length=255, null=True, blank=True)
    license_p = RichTextField(null=True, blank=True)
    license_type = models.CharField(max_length=255, null=True, blank=True)
    language = models.ForeignKey(
        Language, on_delete=models.SET_NULL, null=True, blank=True
    )
    autocomplete_search_field = "license_p"

    def autocomplete_label(self):
        return str(self.license_p)
    
    panels =[
        FieldPanel("url"),
        FieldPanel("license_p"),
        FieldPanel("license_type"),
        AutocompletePanel("language"),
    ]

    @classmethod
    def get(
        cls,
        url,
        license_p,
        language,
        ):
        if url:
            return cls.objects.get(url=url, language=language)
        if license_p:
            return cls.objects.get(license_p=license_p, language=language)
        raise Exception("License.get requires url, language or url paramenter")

    @classmethod
    def create_or_update(cls, url, license_p, license_type, language, creator):
        try:
            return cls.get(
                url=url,
                license_p=license_p,
                language=language,
            )
        except cls.DoesNotExist:
            license = cls()
            license.url = url
            license.creator = creator
            license.license_p = license_p
        
        license.license_type = license_type
        license.language = language
        license.updated_by = creator
        license.save()
        return license

    class Meta:
        verbose_name = _("License")
        verbose_name_plural = _("Licenses")

    def __unicode__(self):
        return self.url or self.license_p or ""

    def __str__(self):
        return self.url or self.license_p or ""
