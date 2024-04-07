from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from core.models import (
    CommonControlField,
    TextWithLang,
)
from wagtail.models import Orderable
from wagtail.admin.panels import InlinePanel, FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel
from journal.models import Journal
from issue.models import Issue


class JournalTOC(CommonControlField, ClusterableModel):
    journal = models.ForeignKey(
        Journal,
        verbose_name=_("Journal"),
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    panels = [
        AutocompletePanel("journal"),
        InlinePanel("journal_section_code", label=_("Journal Section Code"), classname="collapsed"),
        InlinePanel("journal_section", label=_("Journal Section"), classname="collapsed"),
    ]
    

class JournalSectionCode(Orderable, CommonControlField, ClusterableModel):
    journal_section_code = ParentalKey(
        JournalTOC,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_section_code",
    )

    code = models.TextField(_("Code"), null=True, blank=True)

    panels = [
        FieldPanel("code"),
        InlinePanel("journal_section_title", label=_("Journal Section Title"), classname="collapsed"),
    ]

    autocomplete_search_field = "code"

    def autocomplete_label(self):
        return f"{self.code}"


class JournalSectionTitle(Orderable, TextWithLang, CommonControlField):
    journal_section_title = ParentalKey(
        JournalSectionCode,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_section_title",
    )


class JournalSection(Orderable, CommonControlField):
    journal_section = ParentalKey(
        JournalTOC,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_section",
    )

    section = models.TextField(_("Section"), null=True, blank=True)


class IssueTOC(CommonControlField):
    issue = models.ForeignKey(
        Issue,
        verbose_name=_("Issue"),
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    journal_section_code = models.ManyToManyField(
        "JournalSectionCode",
        verbose_name=_("Journal Section Code"),
        blank=True,
    )

    panels = [
        AutocompletePanel("issue"),
        AutocompletePanel("journal_section_code"),
    ]