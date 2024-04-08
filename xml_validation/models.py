from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel

from core.models import CommonControlField


class ValidationConfiguration(CommonControlField):
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
        FieldPanel("key"),
        FieldPanel("value"),
    ]

    def __str__(self): 
        return f"{self.key}: {self.value}"
