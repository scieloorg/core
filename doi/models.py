from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.choices import LANGUAGE
from core.forms import CoreAdminModelForm
from core.models import CommonControlField, Language

from .choices import STATUS


class DOI(CommonControlField):
    value = models.CharField(_("Value"), max_length=100, null=True, blank=True)
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        verbose_name=_("Language"),
        null=True,
        blank=True,
    )
    autocomplete_search_field = "value"

    panels = [
        FieldPanel("value"),
        AutocompletePanel("language"),
    ]

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "value",
                ]
            ),
            models.Index(
                fields=[
                    "language",
                ]
            ),
        ]

    def autocomplete_label(self):
        return str(self.value)

    @property
    def data(self):
        return {
            "doi__value": self.value,
            "doi__language": self.language,
        }

    def __unicode__(self):
        return "%s - %s" % (self.value, self.language) or ""

    def __str__(self):
        return "%s - %s" % (self.value, self.language) or ""

    @classmethod
    def get_or_create(cls, value, language, creator):
        try:
            return cls.objects.get(value=value, language=language)
        except cls.DoesNotExist:
            doi = cls()
            doi.value = value
            doi.language = language
            doi.creator = creator
            doi.save()
            return doi

    base_form_class = CoreAdminModelForm


class DOIRegistration(CommonControlField):
    doi = models.ManyToManyField(DOI, verbose_name="DOI", blank=True)
    submission_date = models.DateField(
        _("Submission Date"), max_length=20, null=True, blank=True
    )
    status = models.CharField(
        _("Status"), choices=STATUS, max_length=15, null=True, blank=True
    )

    panels = [
        AutocompletePanel("doi"),
        FieldPanel("submission_date"),
        FieldPanel("status"),
    ]

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "submission_date",
                ]
            ),
            models.Index(
                fields=[
                    "status",
                ]
            ),
        ]

    @property
    def data(self):
        return {
            "doi_registration__doi": self.doi,
            "doi_registration__submission_date": self.submission_date,
            "doi_registration__status": self.status,
        }

    def __unicode__(self):
        return "%s - %s - %s" % (self.doi, self.submission_date, self.status) or ""

    def __str__(self):
        return "%s - %s - %s" % (self.doi, self.submission_date, self.status) or ""

    base_form_class = CoreAdminModelForm
