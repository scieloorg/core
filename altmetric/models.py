from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel

from . import choices


class RawAltmetric(models.Model):
    issn_scielo = models.CharField(
        _("ISSN SciELO"), max_length=9, null=False, blank=False
    )
    extraction_date = models.CharField(
        _("Extraction Date"), max_length=26, null=False, blank=False
    )
    resource_type = models.CharField(
        _("Resource Type"),
        max_length=10,
        choices=choices.TYPE_OF_RESOURCE,
        null=False,
        blank=False,
    )
    json = models.JSONField(_("JSON File"), null=True, blank=True)

    def __unicode__(self):
        return self.issn_scielo

    def __str__(self):
        return self.issn_scielo

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "issn_scielo",
                ]
            ),
            models.Index(
                fields=[
                    "resource_type",
                ]
            ),
        ]

    panels = [
        FieldPanel("issn_scielo"),
        FieldPanel("extraction_date"),
        FieldPanel("resource_type"),
        FieldPanel("json"),
    ]
