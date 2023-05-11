from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel

from core.forms import CoreAdminModelForm
from core.models import CommonControlField, RichTextWithLang
from journal.models import ScieloJournal


class Issue(CommonControlField):
    """
    Class that represent an Issue
    """
    
    journal = models.ForeignKey(
        ScieloJournal,
        verbose_name=_("Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    number = models.CharField(_("Issue number"), max_length=20, null=True, blank=True)
    volume = models.CharField(_("Issue volume"), max_length=20, null=True, blank=True)
    season = models.CharField(_("Issue season"), max_length=20, null=True, blank=True, help_text="Ex: Jan-Abr.")
    year = models.CharField(_("Issue year"), max_length=20, null=True, blank=True)
    month = models.CharField(_("Issue month"), max_length=20, null=True, blank=True)
    supplement = models.CharField(_("Supplement"), max_length=20, null=True, blank=True)

    panels = [
        FieldPanel("journal"),
        FieldPanel("number"),
        FieldPanel("volume"),
        FieldPanel("year"),
        FieldPanel("month"),
        FieldPanel("supplement"),
    ]

    class Meta:
        verbose_name = _("Issue")
        verbose_name_plural = _("Issues")
        indexes = [
            models.Index(
                fields=[
                    "number",
                ]
            ),
            models.Index(
                fields=[
                    "volume",
                ]
            ),
            models.Index(
                fields=[
                    "year",
                ]
            ),
            models.Index(
                fields=[
                    "month",
                ]
            ),
            models.Index(
                fields=[
                    "supplement",
                ]
            ),
        ]

    @property
    def data(self):
        d = dict
        if self.journal:
            d.update(self.journal.data)
        d.update(
            {
                "issue__number": self.number,
                "issue__volume": self.volume,
                "issue__season": self.season,
                "issue__year": self.year,
                "issue__month": self.month,
                "issue__supplement": self.supp,
            }
        )
        return d

    @classmethod
    def get_or_create(cls, journal, number, volume, season, year, month, supplement, user):
        issues = cls.objects.filter(
            creator=user,
            journal=journal,
            number=number,
            volume=volume,
            season=season,
            year=year,
            month=month,
            supplement=supplement,
        )
        try:
            issue = issues[0]
        except IndexError:
            issue = cls()
            issue.journal = journal
            issue.number = number
            issue.volume = volume
            issue.season = season
            issue.year = year
            issue.month = month
            issue.supplement = supplement
            issue.save()

        return issue

    def __unicode__(self):
        return (
            "%s - (%s %s %s %s)"
            % (self.journal, self.number, self.volume, self.year, self.supplement)
            or ""
        )

    def __str__(self):
        return (
            "%s - (%s %s %s %s)"
            % (self.journal, self.number, self.volume, self.year, self.supplement)
            or ""
        )

    base_form_class = CoreAdminModelForm
