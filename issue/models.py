from django.db import IntegrityError, models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core import choices
from core.forms import CoreAdminModelForm
from core.models import (
    CommonControlField,
    Language,
    License,
    TextLanguageMixin,
    TextWithLang,
)
from journal.models import Journal
from location.models import City

from .exceptions import TocSectionGetError


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
    code_sections = models.ManyToManyField("CodeSectionIssue", blank=True)
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

    autocomplete_search_field = "journal__title"

    def autocomplete_label(self):
        return str(self)

    panels_issue = [
        AutocompletePanel("journal"),
        FieldPanel("volume"),
        FieldPanel("number"),
        FieldPanel("supplement"),
        AutocompletePanel("city"),
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
        AutocompletePanel("sections"),
    ]

    panels_license = [
        AutocompletePanel("license"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_issue, heading=_("Issue")),
            ObjectList(panels_title, heading=_("Titles")),
            ObjectList(panels_subtitle, heading=_("Subtitle")),
            ObjectList(panels_summary, heading=_("Sections")),
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
        values= (self.volume, self.number, self.supplement)
        labels = ("volume", "number", "suppl")
        issue_info = ", ".join([f"{label}: {value}" for label, value in zip(labels, values) if value])

        return "%s, %s, %s" % (self.journal, issue_info, self.year)

    def __str__(self):
        values= (self.volume, self.number, self.supplement)
        labels = ("volume", "number", "suppl")
        issue_info = ", ".join([f"{label}: {value}" for label, value in zip(labels, values) if value])

        return "%s, %s, %s" % (self.journal, issue_info, self.year)


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

    panels = [FieldPanel("title"), AutocompletePanel("language")]

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


class TocSection(TextLanguageMixin, CommonControlField):
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
    autocomplete_search_field = "plain_text"

    def autocomplete_label(self):
        return str(self.plain_text)

    class Meta:
        verbose_name = _("TocSection")
        verbose_name_plural = _("TocSections")
        unique_together = [("plain_text", "language")]
        indexes = [
            models.Index(
                fields=[
                    "plain_text",
                ]
            ),
        ]

    @classmethod
    def get(
        cls,
        value,
        language,
    ):
        if value and language:
            try:
                return cls.objects.get(plain_text=value, language=language)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(plain_text=value, language=language).first()
        raise TocSectionGetError(
            "TocSection.get requires value and language parameters"
        )

    @classmethod
    def create(
        cls,
        value, 
        language,
        user,
    ):
        try:
            obj = cls()
            obj.plain_text = value
            obj.language = language
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(value=value, language=language)

    @classmethod
    def get_or_create(
        cls,
        value,
        language,
        user,
    ):
        try:
            return cls.get(value=value, language=language)
        except cls.DoesNotExist:
            return cls.create(value=value, language=language, user=user)

    def __unicode__(self):
        return f"{self.plain_text} - {self.language}"

    def __str__(self):
        return f"{self.plain_text} - {self.language}"


class CodeSectionIssue(CommonControlField):
    code = models.CharField(_("Code"), max_length=40, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.text} ({self.language.code2 if self.language else 'N/A'})"
    

class SectionIssue(TextWithLang, CommonControlField):
    code_section = models.ForeignKey(
        CodeSectionIssue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.code}"
    
    class Meta:
        unique_together = [("code_section", "language")]

    def __str__(self):
        return f"{self.code_section.code} - {self.text} ({self.language.code2 if self.language else 'N/A'})"