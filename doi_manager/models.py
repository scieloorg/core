from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField


class CrossRefConfiguration(CommonControlField):
    prefix = models.CharField(_("Prefix"), null=True, blank=True, max_length=10)
    depositor_name = models.CharField(_("Depositor Name"), null=True, blank=True, max_length=64)
    depositor_email_address = models.EmailField(_("Depositor e-mail"), null=True, blank=True, max_length=64)
    registrant = models.CharField(_("Registrant"), null=True, blank=True, max_length=64)
    crossmark_policy_url = models.URLField(
        _("Crossmark Policy URL"), null=True, blank=True,
        help_text=_("URL of the journal crossmark policy page"),
    )
    crossmark_policy_doi = models.CharField(
        _("Crossmark Policy DOI"), null=True, blank=True, max_length=100,
        help_text=_("DOI of the journal crossmark policy"),
    )
    username = models.CharField(
        _("Crossref Username"), null=True, blank=True, max_length=64,
        help_text=_("Username/login for Crossref deposit API"),
    )
    password = models.CharField(
        _("Crossref Password"), null=True, blank=True, max_length=64,
        help_text=_("Password for Crossref deposit API"),
    )
    use_test_server = models.BooleanField(
        _("Use test server"), default=False,
        help_text=_("If checked, deposits will be sent to the Crossref test server"),
    )

    base_form_class = CoreAdminModelForm
    panels = [
        FieldPanel("prefix"),
        FieldPanel("depositor_name"),
        FieldPanel("depositor_email_address"),
        FieldPanel("registrant"),
        FieldPanel("crossmark_policy_url"),
        FieldPanel("crossmark_policy_doi"),
        FieldPanel("username"),
        FieldPanel("password"),
        FieldPanel("use_test_server"),
    ]

    def __str__(self):
        return self.prefix or ""

    @property
    def deposit_url(self):
        if self.use_test_server:
            return "https://test.crossref.org/servlet/deposit"
        return "https://doi.crossref.org/servlet/deposit"

    @property
    def data(self):
        d = {
            "depositor_name": self.depositor_name or "depositor_name",
            "depositor_email_address": self.depositor_email_address or "depositor_email_address",
            "registrant": self.registrant or "registrant",
        }
        if self.crossmark_policy_doi:
            d["crossmark_policy_doi"] = self.crossmark_policy_doi
        if self.crossmark_policy_url:
            d["crossmark_policy_url"] = self.crossmark_policy_url
        return d

    @classmethod
    def get_data(cls, prefix):
        try:
            return cls.objects.get(prefix=prefix).data
        except cls.DoesNotExist:
            return cls().data

    @classmethod
    def get_or_create(cls, user, prefix, depositor_name=None, depositor_email_address=None, registrant=None):
        try:
            obj = cls.objects.get(prefix=prefix)
        except cls.DoesNotExist:
            obj = cls()
            obj.prefix = prefix
            obj.creator = user
        obj.depositor_name = depositor_name or obj.depositor_name
        obj.depositor_email_address = depositor_email_address or obj.depositor_email_address
        obj.registrant = registrant or obj.registrant
        obj.updated_by = user
        obj.save()
        return obj


class CrossRefDeposit(CommonControlField):
    """
    Tracks the status of a DOI deposit submitted to Crossref for an article.
    """

    DEPOSIT_STATUS_PENDING = "pending"
    DEPOSIT_STATUS_SUBMITTED = "submitted"
    DEPOSIT_STATUS_SUCCESS = "success"
    DEPOSIT_STATUS_FAILED = "failed"

    DEPOSIT_STATUS = [
        (DEPOSIT_STATUS_PENDING, _("Pending")),
        (DEPOSIT_STATUS_SUBMITTED, _("Submitted")),
        (DEPOSIT_STATUS_SUCCESS, _("Success")),
        (DEPOSIT_STATUS_FAILED, _("Failed")),
    ]

    article = models.ForeignKey(
        "article.Article",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="crossref_deposits",
        verbose_name=_("Article"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=DEPOSIT_STATUS,
        default=DEPOSIT_STATUS_PENDING,
    )
    submission_date = models.DateTimeField(
        _("Submission Date"), null=True, blank=True,
    )
    response = models.TextField(
        _("Response"), null=True, blank=True,
        help_text=_("Response from Crossref API"),
    )
    detail = models.JSONField(_("Detail"), null=True, blank=True)

    base_form_class = CoreAdminModelForm
    panels = [
        AutocompletePanel("article"),
        FieldPanel("status"),
        FieldPanel("submission_date"),
        FieldPanel("response"),
        FieldPanel("detail"),
    ]

    class Meta:
        verbose_name = _("Crossref Deposit")
        verbose_name_plural = _("Crossref Deposits")
        indexes = [
            models.Index(fields=["status"], name="doi_mgr_deposit_status_idx"),
            models.Index(fields=["submission_date"], name="doi_mgr_deposit_subdate_idx"),
        ]

    def __str__(self):
        return f"{self.article} - {self.status}"
