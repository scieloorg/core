from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtailautocomplete.edit_handlers import AutocompletePanel
from wagtail.admin.panels import FieldPanel

from core.models import CommonControlField


class VersionSPS(CommonControlField):
    version = models.CharField(_("Version SPS"), null=False, blank=False)
    link = models.URLField(null=True, blank=True, verbose_name=_("Link SciELO PS"))
    date = models.DateField(null=True, blank=True)

    autocomplete_search_field  = "version"
    
    class Meta:
        verbose_name = _("Version SPS")
        verbose_name_plural = _("Version SPS")

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.version} - {self.date}"


class ValidationConfiguration(CommonControlField):
    sps_version  = models.ForeignKey(VersionSPS, 
        on_delete=models.CASCADE,
        blank=False, 
        null=False
    )
    key = models.CharField(
        max_length=100, 
        blank=False, 
        null=False,
    )
    value = models.JSONField()

    class Meta:
        verbose_name = _("Validation Configuration")
        verbose_name_plural = _("Validation Configurations")

    panels = [
        AutocompletePanel("sps_version"),
        FieldPanel("key"),
        FieldPanel("value"),
    ]

    def __str__(self): 
        return f"{self.key}: {self.value}"
