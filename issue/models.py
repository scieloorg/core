from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable

from core.forms import CoreAdminModelForm
from core.models import (
    CommonControlField,
    Language,
    License,
    RichTextWithLang,
    TextWithLang,
)
from journal.models import Journal
from location.models import City


class Issue(CommonControlField, ClusterableModel):
    """
    Class that represent an Issue
    """

    journal = models.ForeignKey(
        Journal,
        verbose_name=_("Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    sections = models.ManyToManyField("TocSection", blank=True)
    license = models.ManyToManyField(License, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    number = models.CharField(_("Issue number"), max_length=20, null=True, blank=True)
    volume = models.CharField(_("Issue volume"), max_length=20, null=True, blank=True)
    season = models.CharField(
        _("Issue season"),
        max_length=20,
        null=True,
        blank=True,
        help_text="Ex: Jan-Abr.",
    )
    year = models.CharField(_("Issue year"), max_length=20, null=True, blank=True)
    month = models.CharField(_("Issue month"), max_length=20, null=True, blank=True)
    supplement = models.CharField(_("Supplement"), max_length=20, null=True, blank=True)

    panels_issue = [
        FieldPanel("journal"),
        FieldPanel("volume"),
        FieldPanel("supplement"),
        FieldPanel("number"),
        FieldPanel("city"),
        FieldPanel("year"),
        FieldPanel("season"),
        FieldPanel("month"),
    ]

    panels_title = [
        InlinePanel("issue_title", label=_("Issue title")),
    ]

    panels_subtitle = [
        InlinePanel("bibliographic_strip"),
    ]

    panels_summary = [
        FieldPanel("sections"),
    ]

    panels_license = [
        FieldPanel("license"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_issue, heading=_("Issue")),
            ObjectList(panels_title, heading=_("Titles")),
            ObjectList(panels_subtitle, heading=_("Subtitle")),
            ObjectList(panels_summary, heading=_("Summary")),
            ObjectList(panels_license, heading=_("License")),
        ]
    )

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
            models.Index(
                fields=[
                    "season",
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
                "issue__supplement": self.supplement,
            }
        )
        return d

    @property
    def bibliographic(self):
        data = self.bibliographic_strip.all().values(
            "text",
            "language__code2",
        )
        return [
            {
                "text": obj.get("text"),
                "language": obj.get("language__code2"),
            }
            for obj in data
        ]

    @classmethod
    def get_or_create(
        cls,
        journal,
        number,
        volume,
        season,
        year,
        month,
        supplement,
        user,
        sections=None,
    ):
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
            issue.creator = user
            issue.save()
            if sections:
                issue.sections.set(sections)

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


class IssueTitle(Orderable, CommonControlField):
    issue = ParentalKey(
        Issue,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="issue_title",
    )
    title = models.CharField(_("Issue Title"), max_length=100, blank=True, null=True)
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "title",
                ]
            ),
        ]

    def __str__(self):
        return self.title


class BibliographicStrip(Orderable, TextWithLang, CommonControlField):
    issue = ParentalKey(
        Issue,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bibliographic_strip",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "text",
                ]
            ),
        ]

    def __str__(self):
        return self.subtitle


class TocSection(RichTextWithLang, CommonControlField):
    """
    <article-categories>
        <subj-group subj-group-type="heading">
          <subject>NOMINATA</subject>
        </subj-group>
      </article-categories>
    """

    text = RichTextField(
        max_length=100, blank=True, null=True, help_text="For JATs is subject."
    )

    class Meta:
        verbose_name = _("TocSection")
        verbose_name_plural = _("TocSections")
        indexes = [
            models.Index(
                fields=[
                    "text",
                ]
            ),
            models.Index(
                fields=[
                    "plain_text",
                ]
            ),
        ]

    def __unicode__(self):
        return f"{self.text} - {self.language}"

    def __str__(self):
        return f"{self.plain_text}"
