from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField


class CrossRefConfiguration(CommonControlField):
    prefix = models.CharField(
        _("Prefix"),
        null=True,
        blank=True,
        max_length=10,
        help_text=_("DOI prefix assigned to the journal (e.g. 10.1590)."),
    )
    depositor_name = models.CharField(
        _("Depositor Name"),
        null=True,
        blank=True,
        max_length=64,
        help_text=_("Name of the organization depositing the DOI metadata with CrossRef."),
    )
    depositor_email_address = models.EmailField(
        _("Depositor e-mail"),
        null=True,
        blank=True,
        max_length=64,
        help_text=_("E-mail address of the depositor, used by CrossRef for deposit notifications."),
    )
    registrant = models.CharField(
        _("Registrant"),
        null=True,
        blank=True,
        max_length=64,
        help_text=_("Name of the registrant organization responsible for the DOI prefix."),
    )
    password = models.CharField(
        _("Password"),
        null=True,
        blank=True,
        max_length=64,
        help_text=_("Password for authenticating with the CrossRef deposit API."),
    )

    autocomplete_search_field = "prefix"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        if self.prefix:
            return self.prefix
        if self.depositor_name:
            return self.depositor_name
        return _("CrossRef Configuration")

    base_form_class = CoreAdminModelForm
    panels = [
        FieldPanel("depositor_name"),
        FieldPanel("depositor_email_address"),
        FieldPanel("registrant"),
        FieldPanel("prefix"),
        FieldPanel("password"),
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
        try:
            return cls.objects.get(prefix=prefix).data
        except cls.DoesNotExist:
            return cls().data
