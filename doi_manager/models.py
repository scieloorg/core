from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField


class CrossRefConfiguration(CommonControlField):
    prefix = models.CharField(_("Prefix"), null=True, blank=True, max_length=10)
    depositor_name = models.CharField(_("Depositor Name"), null=True, blank=True, max_length=64)
    depositor_email_address = models.EmailField(_("Depositor e-mail"), null=True, blank=True, max_length=64)
    registrant = models.CharField(_("Registrant"), null=True, blank=True, max_length=64)

    base_form_class = CoreAdminModelForm
    panels = [
        FieldPanel("depositor_name"),
        FieldPanel("depositor_email_address"),
        FieldPanel("registrant"),
        FieldPanel("prefix"),
    ]

    @property
    def data(self):
        return {
            "depositor_name": self.depositor_name or "depositor_name",
            "depositor_email_address": self.depositor_email_address or "depositor_email_address",
            "registrant": self.registrant or "registrant",
        }

    @classmethod
    def get_data(cls, prefix):
        return cls.objects.get(prefix=prefix).data

