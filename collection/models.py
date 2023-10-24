from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, TextWithLang
from core.models import Language
from . import choices
from django.utils.translation import get_language

class CollectionName(TextWithLang):
    autocomplete_search_filter = "text"

    def autocomplete_label(self):
        return str(self)

    @property
    def data(self):
        d = {
            "collection_name__text": self.text,
            "collection_name__language": self.language,
        }

        return d

    def __unicode__(self):
        return "%s (%s)" % (self.text, self.language)

    def __str__(self):
        return "%s (%s)" % (self.text, self.language)


class Collection(CommonControlField):
    acron3 = models.CharField(
        _("Acronym with 3 chars"), max_length=10, null=True, blank=True
    )
    acron2 = models.CharField(
        _("Acronym with 2 chars"), max_length=10, null=True, blank=True
    )
    code = models.CharField(_("Code"), max_length=10, null=True, blank=True)
    domain = models.URLField(_("Domain"), null=True, blank=True)
    name = models.ManyToManyField(
        CollectionName, verbose_name="Collection Name", blank=True
    )
    main_name = models.TextField(_("Main name"), null=True, blank=True)
    status = models.TextField(
        _("Status"), choices=choices.STATUS, null=True, blank=True
    )
    has_analytics = models.BooleanField(_("Has analytics"), null=True, blank=True)
    # Antes era type
    collection_type = models.TextField(
        _("Collection Type"), choices=choices.TYPE, null=True, blank=True
    )
    is_active = models.BooleanField(_("Is active"), null=True, blank=True)
    foundation_date = models.DateField(_("Foundation data"), null=True, blank=True)

    autocomplete_search_field = "main_name"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("acron3"),
        FieldPanel("acron2"),
        FieldPanel("code"),
        FieldPanel("domain"),
        AutocompletePanel("name"),
        FieldPanel("main_name"),
        FieldPanel("status"),
        FieldPanel("has_analytics"),
        FieldPanel("collection_type"),
        FieldPanel("is_active"),
        FieldPanel("foundation_date"),
    ]

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
            "collection__is_foundation_date": self.foundation_date,
        }

        if self.name:
            d.update(self.name.data)

        return d

    def __unicode__(self):
        return "%s" % self.main_name or ""

    def __str__(self):
        lang = Language.get_or_create(code2=get_language())
        try:
            return f"{self.name.all().filter(language=lang)[0].text}"
        except IndexError:
            return f"{self.main_name}" or "" 

    base_form_class = CoreAdminModelForm
