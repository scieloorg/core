import csv
import logging
import re
import os

from django.contrib.auth import get_user_model
from django.db import models, IntegrityError
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from collection.models import Collection
from core.choices import MONTHS
from core.forms import CoreAdminModelForm
from core.models import (
    CommonControlField,
    Language,
    License,
    RichTextWithLanguage,
    TextWithLang,
    FileWithLang,
)
from institution.models import (
    Publisher,
    CopyrightHolder,
    Owner,
    Sponsor,
    BaseHistoryItem,
)
from journal.exceptions import (
    IndexedAtCreationOrUpdateError,
    JournalCreateOrUpdateError,
    JournalGetError,
    MissionCreateOrUpdateError,
    MissionGetError,
    OfficialJournalCreateOrUpdateError,
    OfficialJournalGetError,
    SciELOJournalCreateOrUpdateError,
    SciELOJournalGetError,
    StandardCreationOrUpdateError,
    SubjectCreationOrUpdateError,
    WosdbCreationOrUpdateError,
    TitleInDatabaseCreationOrUpdateError,
)
from location.models import Location
from vocabulary.models import Vocabulary
from thematic_areas.models import ThematicArea

from . import choices

User = get_user_model()


class OfficialJournal(CommonControlField, ClusterableModel):
    """
    Class that represent the Official Journal
    """

    title = models.TextField(_("ISSN Title"), null=True, blank=True)
    iso_short_title = models.TextField(_("ISO Short Title"), null=True, blank=True)
    new_title = models.ForeignKey(
        "self",
        verbose_name=_("New Title"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_title_journal",
    )
    old_title = models.ManyToManyField("self", blank=True)
    previous_journal_titles = models.TextField(_("Previous Journal titles"),null=True, blank=True)
    next_journal_title = models.TextField(_("Next Journal Title"), null=True, blank=True)
    initial_year = models.CharField(
        _("Initial Year"), max_length=4, blank=True, null=True
    )
    initial_month = models.CharField(
        _("Month Year"), max_length=2, choices=MONTHS, blank=True, null=True
    )
    initial_volume = models.CharField(
        _("Initial Volume"), max_length=32, null=True, blank=True
    )
    initial_number = models.CharField(
        _("Initial Number"), max_length=32, null=True, blank=True
    )
    terminate_year = models.CharField(
        _("Termination year"), max_length=4, null=True, blank=True
    )
    terminate_month = models.CharField(
        _("Termination month"), max_length=2, choices=MONTHS, null=True, blank=True
    )
    final_volume = models.CharField(
        _("Final Volume"), max_length=32, null=True, blank=True
    )
    final_number = models.CharField(
        _("Final Number"), max_length=32, null=True, blank=True
    )
    issn_print = models.CharField(_("ISSN Print"), max_length=9, null=True, blank=True)
    issn_electronic = models.CharField(
        _("ISSN Eletronic"), max_length=9, null=True, blank=True
    )
    issn_print_is_active = models.BooleanField(verbose_name=_("ISSN Print is active"), default=False)
    issnl = models.CharField(_("ISSNL"), max_length=9, null=True, blank=True)

    panels_titles = [
        FieldPanel("title"),
        FieldPanel("iso_short_title"),
        InlinePanel("parallel_title", label=_("Parallel titles")),
        AutocompletePanel("old_title"),
        AutocompletePanel("new_title"),
        FieldPanel("previous_journal_titles"),
        FieldPanel("next_journal_title"),
    ]

    panels_dates = [
        FieldPanel("initial_year"),
        FieldPanel("initial_month"),
        FieldPanel("terminate_year"),
        FieldPanel("terminate_month"),
        FieldPanel("initial_volume"),
        FieldPanel("initial_number"),
        FieldPanel("final_volume"),
        FieldPanel("final_number"),
    ]

    panels_issns = [
        FieldPanel("issn_print"),
        FieldPanel("issn_print_is_active"),
        FieldPanel("issn_electronic"),
        FieldPanel("issnl"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_titles, heading=_("Titles")),
            ObjectList(panels_dates, heading=_("Dates")),
            ObjectList(panels_issns, heading=_("Issns")),
        ]
    )

    base_form_class = CoreAdminModelForm

    class Meta:
        verbose_name = _("ISSN Journal")
        verbose_name_plural = _("ISSN Journals")
        indexes = [
            models.Index(
                fields=[
                    "title",
                ]
            ),
            models.Index(
                fields=[
                    "initial_year",
                ]
            ),
            models.Index(
                fields=[
                    "issn_print",
                ]
            ),
            models.Index(
                fields=[
                    "issn_electronic",
                ]
            ),
            models.Index(
                fields=[
                    "issnl",
                ]
            ),
        ]
        ordering = ["title"]

    autocomplete_search_field = "title"

    def autocomplete_label(self):
        return str(self)

    def __unicode__(self):
        return f"{self.title}"

    def __str__(self):
        return f"{self.title}"

    @property
    def data(self):
        d = {
            "official_journal__title": self.title,
            "official_journal__initial_year": self.initial_year,
            "official_journal__issn_print": self.issn_print,
            "official_journal__issn_electronic": self.issn_electronic,
            "official_journal__issnl": self.issnl,
        }
        return d

    @classmethod
    def get(cls, issn_print=None, issn_electronic=None, issnl=None):
        filters = Q()

        if issn_print:
            filters |= Q(issn_print=issn_print)
        if issn_electronic:
            filters |= Q(issn_electronic=issn_electronic)
        if filters:
            return cls.objects.get(filters)
        if issnl:
            return cls.objects.get(issnl=issnl)
        raise OfficialJournalGetError(
            "OfficialJournal.get requires issn_print or issn_electronic or issnl"
        )

    @classmethod
    def create_or_update(
        cls,
        user,
        issn_print=None,
        issn_electronic=None,
        issnl=None,
        title=None,
        issn_print_is_active=None,
    ):
        try:
            obj = cls.get(
                issn_print=issn_print, issn_electronic=issn_electronic, issnl=issnl
            )
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
        except (OfficialJournalGetError, cls.MultipleObjectsReturned) as e:
            raise OfficialJournalCreateOrUpdateError(
                _("Unable to create or update official journal {}").format(e)
            )

        obj.issnl = issnl or obj.issnl
        obj.issn_electronic = issn_electronic or obj.issn_electronic
        obj.issn_print = issn_print or obj.issn_print
        obj.title = title or obj.title
        obj.issn_print_is_active = issn_print_is_active or obj.issn_print_is_active
        obj.save()

        return obj

    def add_old_title(self, user, title):
        if not title:
            return
        old_title = None
        for item in OfficialJournal.objects.filter(title=title).iterator():
            old_title = item
            break
        if not old_title:
            old_title = OfficialJournal.objects.create(title=title, creator=user)
        self.old_title.add(old_title)
        self.save()

    def add_new_title(self, user, title):
        if not title:
            return
        new_title = None
        for item in OfficialJournal.objects.filter(title=title).iterator():
            new_title = item
            break
        if not new_title:
            new_title = OfficialJournal.objects.create(title=title, creator=user)
        self.new_title = new_title
        self.save()

    @property
    def parallel_titles(self):
        return JournalParallelTitle.objects.filter(official_journal=self)


class SocialNetwork(models.Model):
    name = models.CharField(
        _("Name"), choices=choices.SOCIAL_NETWORK_NAMES, max_length=20, null=True, blank=True
    )
    url = models.URLField(_("URL"), null=True, blank=True)

    panels = [FieldPanel("name"), FieldPanel("url")]

    class Meta:
        verbose_name = _("Social Network")
        verbose_name_plural = _("Social Networks")
        indexes = [
            models.Index(
                fields=[
                    "name",
                ]
            ),
            models.Index(
                fields=[
                    "url",
                ]
            ),
        ]
        abstract = True

    @property
    def data(self):
        d = {"social_network__name": self.name, "social_network__url": self.url}

        return d


class Journal(CommonControlField, ClusterableModel):
    """
    A class used to represent a journal model designed in the SciELO context.

    Attributes
    ----------
    official : official journal class object
        journal model that contains only official data registered in the ISSN.

    Methods
    -------
    TODO
    """

    official = models.ForeignKey(
        OfficialJournal,
        verbose_name=_("ISSN Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    title = models.TextField(_("Journal Title"), null=True, blank=True)
    short_title = models.TextField(_("Short Title"), null=True, blank=True)
    logo = models.ForeignKey(
        "wagtailimages.Image",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    submission_online_url = models.URLField(
        _("Submission online URL"), null=True, blank=True
    )

    contact_name = models.TextField(null=True, blank=True)
    contact_address = models.TextField(_("Address"), null=True, blank=True)
    contact_location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True
    )

    open_access = models.CharField(
        _("Open Access status"),
        max_length=10,
        choices=choices.OA_STATUS,
        null=True,
        blank=True,
    )

    url_oa = models.URLField(
        _("Open Science accordance form"),
        null=True,
        blank=True,
        help_text=mark_safe(
            _(
                """Suggested form: <a target='_blank' href='https://wp.scielo.org/wp-content/uploads/Formulario-de-Conformidade-Ciencia-Aberta.docx'>https://wp.scielo.org/wp-content/uploads/Formulario-de-Conformidade-Ciencia-Aberta.docx</a>"""
            )
        ),
    )
    main_collection = models.ForeignKey(
        Collection,
        verbose_name=_("Main Collection"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    frequency = models.CharField(
        _("Frequency"),
        max_length=4,
        choices=choices.FREQUENCY,
        null=True,
        blank=True,
    )
    publishing_model = models.CharField(
        _("Publishing Model"),
        max_length=16,
        choices=choices.PUBLISHING_MODEL,
        null=True,
        blank=True,
    )
    subject_descriptor = models.ManyToManyField(
        "SubjectDescriptor",
        verbose_name=_("Subject Descriptors"),
        blank=True,
    )
    subject = models.ManyToManyField(
        "Subject",
        verbose_name=_("Study Areas"),
        blank=True,
    )
    wos_db = models.ManyToManyField(
        "WebOfKnowledge",
        verbose_name=_("Web of Knowledge Databases"),
        blank=True,
    )
    wos_area = models.ManyToManyField(
        "WebOfKnowledgeSubjectCategory",
        verbose_name=_("Web of Knowledge Subject Categories"),
        blank=True,
    )
    text_language = models.ManyToManyField(
        Language,
        verbose_name=_("Text Languages"),
        related_name="text_language",
        blank=True,
    )
    abstract_language = models.ManyToManyField(
        Language,
        verbose_name=_("Abstract Languages"),
        related_name="abstract_language",
        blank=True,
    )
    standard = models.ForeignKey(
        "Standard",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    alphabet = models.CharField(
        _("Alphabet"),
        max_length=4,
        choices=choices.ALPHABET_OF_TITLE,
        null=True,
        blank=True,
    )
    type_of_literature = models.CharField(
        _("Type of Literature"),
        max_length=4,
        choices=choices.LITERATURE_TYPE,
        null=True,
        blank=True,
    )
    treatment_level = models.CharField(
        _("Treatment Level"),
        max_length=4,
        choices=choices.TREATMENT_LEVEL,
        null=True,
        blank=True,
    )
    level_of_publication = models.CharField(
        _("Level of Publication"),
        max_length=2,
        choices=choices.PUBLICATION_LEVEL,
        null=True,
        blank=True,
    )
    national_code = models.TextField(
        _("National Code"),
        null=True,
        blank=True,
    )
    classification = models.TextField(
        _("Classification"),
        null=True,
        blank=True,
    )
    vocabulary = models.ForeignKey(
        Vocabulary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    indexed_at = models.ManyToManyField(
        "IndexedAt",
        verbose_name=_("Indexed At"),
        blank=True,
    )
    additional_indexed_at = models.ManyToManyField(
        "AdditionalIndexedAt",
        verbose_name=_("Additional Index At"),
        blank=True,
    )
    journal_url = models.URLField(
        _("Journal URL"),
        null=True,
        blank=True,
    )
    use_license = models.ForeignKey(
        License,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    center_code = models.TextField(
        _("Center code"),
        blank=True,
        null=True,
    )
    identification_number = models.CharField(
        _("Identification Number"),
        max_length=9,
        blank=True,
        null=True,
    )
    ftp = models.CharField(
        _("Ftp"),
        max_length=3,
        blank=True,
        null=True,
    )
    user_subscription = models.CharField(
        _("User Subscription"),
        max_length=3,
        blank=True,
        null=True,
    )
    subtitle = models.TextField(
        _("Subtitle"),
        blank=True,
        null=True,
    )
    section = models.CharField(
        _("Section"),
        max_length=255,
        blank=True,
        null=True,
    )
    has_supplement = models.TextField(
        _("Has Supplement"),
        blank=True,
        null=True,
    )
    is_supplement = models.CharField(
        _("Is supplement"),
        max_length=255,
        blank=True,
        null=True,
    )
    acronym_letters = models.CharField(
        _("Acronym Letters"),
        max_length=8,
        blank=True,
        null=True,
    )
    author_name = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Authors names"),
        help_text=_(
            "For compound surnames, create clear identification [uppercase, bold, and/or hyphen]"
        ),
    )
    manuscript_length = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("Manuscript Length"),
        help_text=_("Manuscript Length (consider spacing)"),
    )
    format_check_list = models.ManyToManyField(
        "ArticleSubmissionFormatCheckList",
        blank=True,
    )
    digital_pa = models.ManyToManyField(
        "DigitalPreservationAgency",
        blank=True,
        verbose_name=_("DigitalPreservationAgency"),
    )
    valid = models.BooleanField(default=False, null=True, blank=True)

    autocomplete_search_field = "title"

    def autocomplete_label(self):
        return str(self)

    panels_titles = [
        AutocompletePanel("official"),
        FieldPanel("title"),
        FieldPanel("short_title"),
        InlinePanel("other_titles", label=_("Other titles"), classname="collapsed"),
    ]

    panels_scope_and_about = [
        AutocompletePanel("indexed_at"),
        AutocompletePanel("additional_indexed_at"),
        FieldPanel("subject"),
        AutocompletePanel("subject_descriptor"),
        InlinePanel("thematic_area", label=_("Thematic Areas"), classname="collapsed"),
        FieldPanel("wos_db"),
        AutocompletePanel("wos_area"),
        InlinePanel("mission", label=_("Mission"), classname="collapsed"),
        InlinePanel("history", label=_("Brief History"), classname="collapsed"),
        InlinePanel("focus", label=_("Focus and Scope"), classname="collapsed"),
    ]

    panels_institutions = [
        InlinePanel("owner_history", label=_("Owner"), classname="collapsed"),
        InlinePanel("publisher_history", label=_("Publisher"), classname="collapsed"),
        InlinePanel("sponsor_history", label=_("Sponsor"), classname="collapsed"),
        InlinePanel(
            "copyright_holder_history",
            label=_("Copyright Holder"),
            classname="collapsed",
        ),
    ]

    panels_website = [
        FieldPanel("contact_name"),
        FieldPanel("contact_address"),
        AutocompletePanel("contact_location"),
        InlinePanel("journal_email", label=_("Contact e-mail")),
        FieldPanel("logo", heading=_("Logo")),
        FieldPanel("journal_url"),
        FieldPanel("submission_online_url"),
        FieldPanel("main_collection"),
        InlinePanel("title_in_database", classname='collapsed', label=_("Title in database")),
        InlinePanel("journalsocialnetwork", label=_("Social Network")),
        FieldPanel("frequency"),
        FieldPanel("publishing_model"),
        FieldPanel("standard"),
        AutocompletePanel("vocabulary"),
    ]

    panels_open_science = [
        FieldPanel("open_access"),
        FieldPanel("url_oa"),
        InlinePanel(
            "file_oa", label=_("Open Science accordance form"), classname="collapsed"
        ),
        FieldPanel("use_license"),
        InlinePanel("open_data", label=_("Open data"), classname="collapsed"),
        InlinePanel("preprint", label=_("Preprint"), classname="collapsed"),
        InlinePanel("review", label=_("Peer review"), classname="collapsed"),
    ]

    panels_policy = [
        InlinePanel(
            "ethics",
            label=_("Ethics"),
            classname="collapsed",
        ),
        InlinePanel(
            "ecommittee",
            label=_("Ethics Committee"),
            classname="collapsed",
        ),
        InlinePanel(
            "copyright",
            label=_("Copyright"),
            classname="collapsed",
        ),
        InlinePanel(
            "website_responsibility",
            label=_("Intellectual Property / Terms of use / Website responsibility"),
            classname="collapsed",
        ),
        InlinePanel(
            "author_responsibility",
            label=_("Intellectual Property / Terms of use / Author responsibility"),
            classname="collapsed",
        ),
        InlinePanel(
            "policies",
            label=_("Retraction Policy | Ethics and Misconduct Policy"),
            classname="collapsed",
        ),
        AutocompletePanel("digital_pa"),
        InlinePanel(
            "digital_preservation",
            label=_("Digital Preservation"),
            classname="collapsed",
        ),
        InlinePanel(
            "conflict_policy",
            label=_("Conflict of interest policy"),
            classname="collapsed",
        ),
        InlinePanel(
            "software_adoption",
            label=_("Similarity Verification Software Adoption"),
            classname="collapsed",
        ),
        InlinePanel(
            "gender_issues",
            label=_("Gender Issues"),
            classname="collapsed",
        ),
        InlinePanel(
            "fee_charging",
            label=_("Fee Charging"),
            classname="collapsed",
        ),
    ]
    panels_notes = [InlinePanel("annotation", label=_("Notes"), classname="collapsed")]

    panels_legacy_compatibility_fields = [
        FieldPanel("alphabet"),
        FieldPanel("classification"),
        FieldPanel("national_code"),
        FieldPanel("type_of_literature"),
        FieldPanel("treatment_level"),
        FieldPanel("level_of_publication"),
        FieldPanel("center_code"),
        FieldPanel("identification_number"),
        FieldPanel("ftp"),
        FieldPanel("user_subscription"),
        FieldPanel("subtitle"),
        FieldPanel("section"),
        FieldPanel("has_supplement"),
        FieldPanel("is_supplement"),
        FieldPanel("acronym_letters"),
    ]

    panels_instructions_for_authors = [
        InlinePanel(
            "accepted_documment_types",
            label=_("Accepted Document Types"),
            classname="collapsed",
        ),
        InlinePanel(
            "authors_contributions",
            label=_("Authors Contributions"),
            classname="collapsed",
        ),
        InlinePanel(
            "preparing_manuscript",
            label=_("Preparing Manuscript"),
            classname="collapsed",
        ),
        InlinePanel(
            "digital_assets",
            label=_("Digital Assets"),
            classname="collapsed",
        ),
        InlinePanel(
            "citations_and_references",
            label=_("Citations and References"),
            classname="collapsed",
        ),
        InlinePanel(
            "supp_docs_submission",
            label=_("Supplementary Documents Required for Submission"),
            classname="collapsed",
        ),
        InlinePanel(
            "financing_statement",
            label=_("Financing Statement"),
            classname="collapsed",
        ),
        InlinePanel(
            "acknowledgements",
            label=_("Acknowledgements"),
            classname="collapsed",
        ),
        InlinePanel(
            "additional_information",
            label=_("Additional Information"),
            classname="collapsed",
        ),
        FieldPanel("author_name"),
        FieldPanel("manuscript_length"),
        FieldPanel("format_check_list"),
        AutocompletePanel("text_language"),
        AutocompletePanel("abstract_language"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_titles, heading=_("Titles")),
            ObjectList(panels_scope_and_about, heading=_("Scope and about")),
            ObjectList(panels_institutions, heading=_("Institutions")),
            ObjectList(panels_website, heading=_("Website")),
            ObjectList(panels_open_science, heading=_("Open Science")),
            ObjectList(panels_policy, heading=_("Journal Policy")),
            ObjectList(panels_notes, heading=_("Notes")),
            ObjectList(
                panels_legacy_compatibility_fields, heading=_("Legacy Compatibility")
            ),
            ObjectList(
                panels_instructions_for_authors, heading=_("Instructions for Authors")
            ),
        ]
    )

    class Meta:
        verbose_name = _("Journal")
        verbose_name_plural = _("Journals")
        ordering = ("title",)
        indexes = [
            models.Index(
                fields=[
                    "official",
                ]
            ),
            models.Index(
                fields=[
                    "title",
                ]
            ),
            models.Index(
                fields=[
                    "use_license",
                ]
            ),
            models.Index(
                fields=[
                    "publishing_model",
                ]
            ),
        ]

    def is_indexed_at(self, db_acronym):
        if not db_acronym:
            raise ValueError("Journal.is_indexed_at requires db_acronym")
        try:
            return bool(self.indexed_at.get(acronym=db_acronym))
        except IndexedAt.DoesNotExist:
            return False

    @property
    def data(self):
        d = {}

        if self.official:
            d.update(self.official.data)

        d.update(
            {
                "journal__title": self.title,
                "journal__short_title": self.short_title,
                "journal__submission_online_url": self.submission_online_url,
            }
        )

        return d

    @classmethod
    def get(
        cls,
        official_journal,
    ):
        if official_journal:
            return cls.objects.get(official=official_journal)
        raise JournalGetError("Journal.get requires offical_journal parameter")

    @classmethod
    def create_or_update(
        cls,
        user,
        official_journal,
        title=None,
        short_title=None,
        submission_online_url=None,
        open_access=None,
    ):
        try:
            obj = cls.get(official_journal)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
        except (JournalGetError, cls.MultipleObjectsReturned) as e:
            raise JournalCreateOrUpdateError(
                _("Unable to create or update journal {}").format(e)
            )

        obj.official = official_journal or obj.official
        obj.title = title or obj.title
        obj.short_title = short_title or obj.short_title
        obj.submission_online_url = submission_online_url or obj.submission_online_url
        obj.open_access = open_access or obj.open_access
        obj.save()


        return obj

    def __unicode__(self):
        return f"{self.title}" or f"{self.official}"

    def __str__(self):
        return f"{self.title}" or f"{self.official}"

    base_form_class = CoreAdminModelForm


class FileOpenScience(Orderable, FileWithLang, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="file_oa", null=True
    )
    file = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("File"),
        help_text=mark_safe(
            _(
                """Suggested form: <a target='_blank' href='https://wp.scielo.org/wp-content/uploads/Formulario-de-Conformidade-Ciencia-Aberta.docx'>https://wp.scielo.org/wp-content/uploads/Formulario-de-Conformidade-Ciencia-Aberta.docx</a>"""
            )
        ),
        related_name="+",
    )


class JournalEmail(Orderable):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="journal_email", null=True
    )
    email = models.EmailField()


class Mission(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="mission", null=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "journal",
                ]
            ),
            models.Index(
                fields=[
                    "language",
                ]
            ),
        ]

    @property
    def data(self):
        d = {}

        if self.journal:
            d.update(self.journal.data)

        return d

    @classmethod
    def get(
        cls,
        journal,
        language,
    ):
        if journal and language:
            return cls.objects.filter(journal=journal, language=language)
        raise MissionGetError("Mission.get requires journal and language parameters")

    @classmethod
    def create_or_update(
        cls,
        user,
        journal,
        language,
        mission_rich_text,
    ):
        if not mission_rich_text:
            raise MissionCreateOrUpdateError(
                "Mission.create_or_update requires mission_rich_text parameter"
            )
        try:
            obj = cls.get(journal, language)
            obj.updated_by = user
        except IndexError:
            obj = cls()
            obj.creator = user
        except (MissionGetError, cls.MultipleObjectsReturned) as e:
            raise MissionCreateOrUpdateError(
                _("Unable to create or update journal {}").format(e)
            )
        obj.rich_text = mission_rich_text or obj.rich_text
        obj.language = language or obj.language
        obj.journal = journal or obj.journal
        obj.save()
        return obj


class OwnerHistory(Orderable, BaseHistoryItem):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="owner_history", null=True
    )
    institution = models.ForeignKey(
        Owner,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    panels = [
        AutocompletePanel("institution"),
        FieldPanel("initial_date"),
        FieldPanel("final_date"),
    ]


class PublisherHistory(Orderable, BaseHistoryItem):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="publisher_history", null=True
    )
    institution = models.ForeignKey(
        Publisher,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    panels = [
        AutocompletePanel("institution"),
        FieldPanel("initial_date"),
        FieldPanel("final_date"),
    ]


class SponsorHistory(Orderable, BaseHistoryItem):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, null=True, related_name="sponsor_history"
    )
    institution = models.ForeignKey(
        Sponsor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    panels = [
        AutocompletePanel("institution"),
        FieldPanel("initial_date"),
        FieldPanel("final_date"),
    ]


class CopyrightHolderHistory(Orderable, BaseHistoryItem):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        null=True,
        related_name="copyright_holder_history",
    )
    institution = models.ForeignKey(
        CopyrightHolder,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    
    panels = [
        AutocompletePanel("institution"),
        FieldPanel("initial_date"),
        FieldPanel("final_date"),
    ]


class JournalSocialNetwork(Orderable, SocialNetwork):
    page = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="journalsocialnetwork",
        null=True,
    )


class OpenData(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=mark_safe(
            _(
                """Refers to sharing data, codes, methods and other materials used and 
            resulting from research that are usually the basis of the texts of articles published by journals. 
            Guide: <a target='_blank' href='https://wp.scielo.org/wp-content/uploads/Guia_TOP_pt.pdf'>https://wp.scielo.org/wp-content/uploads/Guia_TOP_pt.pdf</a>"""
            )
        ),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="open_data", null=True
    )


class Preprint(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """A preprint is defined as a manuscript ready for submission to a journal that is deposited 
            with trusted preprint servers before or in parallel with submission to a journal. 
            This practice joins that of continuous publication as mechanisms to speed up research communication. 
            Preprints share with journals the originality in the publication of articles and inhibit the use of 
            the double-blind procedure in the evaluation of manuscripts. 
            The use of preprints is an option and choice of the authors and it is up to the journals to adapt 
            their policies to accept the submission of manuscripts previously deposited in a preprints server 
            recognized by the journal."""
        ),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="preprint", null=True
    )


class History(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            "Insert here a brief history with events and milestones in the trajectory of the journal"
        ),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="history", null=True
    )


class Focus(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_("Insert here the focus and scope of the journal"),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="focus", null=True
    )


class Review(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True, blank=True, help_text=_("Brief description of the review flow")
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="review", null=True
    )


class Ecommittee(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Authors must attach a statement of approval from the ethics committee of 
            the institution responsible for approving the research"""
        ),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="ecommittee", null=True
    )


class Copyright(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Describe the policy used by the journal on copyright issues. 
            We recommend that this section be in accordance with the recommendations of the SciELO criteria, 
            item 5.2.10.1.2. - Copyright"""
        ),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="copyright", null=True
    )


class WebsiteResponsibility(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """EX. DOAJ: Copyright terms applied to posted content must be clearly stated and separate 
            from copyright terms applied to the website"""
        ),
    )
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="website_responsibility",
        null=True,
    )


class AuthorResponsibility(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """The author's declaration of responsibility for the content published in 
            the journal that owns the copyright Ex. DOAJ: The terms of copyright must not contradict 
            the terms of the license or the terms of the open access policy. "All rights reserved" is 
            never appropriate for open access content"""
        ),
    )
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="author_responsibility",
        null=True,
    )


class Policies(Orderable, RichTextWithLanguage, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=mark_safe(
            _(
                """Describe here how the journal will deal with ethical issues and/or 
            issues that may damage the journal's reputation. What is the journal's position regarding 
            the retraction policy that the journal will adopt in cases of misconduct. 
            Best practice guide: <a target='_blank' 
            href='https://wp.scielo.org/wp-content/uploads/Guia-de-Boas-Praticas-para-o-Fortalecimento-da-Etica-na-Publicacao-Cientifica.pdf'>
            https://wp.scielo.org/wp-content/uploads/Guia-de-Boas-Praticas-para-o-Fortalecimento-da-Etica-na-Publicacao-Cientifica.pdf</a>"""
            )
        ),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="policies", null=True
    )


class ConflictPolicy(Orderable, RichTextWithLanguage, CommonControlField):
    """
    Política sobre Conflito de Interesses
    """

    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="conflict_policy", null=True
    )


class SimilarityVerificationSoftwareAdoption(
    Orderable, RichTextWithLanguage, CommonControlField
):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="software_adoption", null=True
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Please describe here if the journal uses any similarity verification software. Describe the policy. What cases are checked?
            At what stage in the workflow are manuscripts verified?"""
        ),
        verbose_name=_("Similarity erification software"),
    )
    policy_description = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            "Describe the policy. Which cases are verified? At what point in the workflow are the manuscripts checked?"
        ),
    )
    software = models.TextField(
        blank=True, null=True, help_text=_("Write the name of the software used.")
    )
    url_software = models.TextField(
        blank=True, null=True, help_text=_("Write the link of the software used.")
    )

    panels = [
        AutocompletePanel("language"),
        FieldPanel("rich_text"),
        FieldPanel("policy_description"),
        FieldPanel("software"),
        FieldPanel("url_software"),
    ]


class GenderIssues(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="gender_issues", null=True
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            "Describe how your journal considers gender diversity in the group of authors, editorial board, and reviewers."
        ),
    )


class FeeCharging(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="fee_charging", null=True
    )
    coin = models.CharField(
        max_length=3,
        null=True,
        blank=True,
        choices=choices.COINS,
    )
    fee_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
    )
    rich_text = RichTextField(
        _("Concepts"),
        null=True,
        blank=True,
        help_text=mark_safe(
            _(
                """Please describe any charges to authors related to the submission or publication of works.
        For article publication: Clearly state when no fees are charged.
        Under what circumstances are charges applicable? Are there any discounts?
        SciELO Statement on Financial Sustainability: <a target='_blank' 
            href='https://mailchi.mp/scielo/declaracao-sobre-sustentabilidade'>
            https://mailchi.mp/scielo/declaracao-sobre-sustentabilidade</a>
        """
            )
        ),
    )
    panels = [
        AutocompletePanel("language"),
        FieldPanel("coin"),
        FieldPanel("fee_charge"),
        FieldPanel("rich_text"),
    ]


class AcceptedDocumentTypes(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="accepted_documment_types",
        null=True,
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Describe the types of documents that can be submitted to the journal.
                    Provide information regarding the positioning related to preprint submissions.
                    Examples: Original Article, Review Article, Preprints and etc."""
        ),
    )


class AuthorsContributions(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="authors_contributions",
        null=True,
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=mark_safe(
            _(
                """Description of how authors contributions should be specified.
        Does it use any taxonomy? If yes, which one?
        Does the article text explicitly state the authors contributions?
        Preferably, use the CREDiT taxonomy structure: <a target='_blank' 
            href='https://casrai.org/credit/'>https://casrai.org/credit/</a>
        """
            )
        ),
    )


class PreparingManuscript(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="preparing_manuscript",
        null=True,
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Specify how authors should present their research and explain why the work is suitable for publication in the journal."""
        ),
    )


class DigitalAssets(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="digital_assets", null=True
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Please describe how tables, charts, figures, illustrations, maps, diagrams, and other digital assets in the documents should be presented for publication in the journal. It is important to specify technical details such as format, resolution, size, etc."""
        ),
    )


class CitationsAndReferences(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="citations_and_references",
        null=True,
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Describe the citation and referencing style used by the journal. Provide examples of document types according to the style."""
        ),
    )


class SuppDocsRequiredForSubmission(
    Orderable, RichTextWithLanguage, CommonControlField
):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="supp_docs_submission",
        null=True,
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Describe any supplementary documents requested from authors during manuscript submission. Examples may include Open Science Compliance Form, authors' agreement statement, ethics committee approval form, etc."""
        ),
    )


class FinancingStatement(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="financing_statement",
        null=True,
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        # TODO
        # Criar help_text
        help_text=_("""???"""),
    )


class Acknowledgements(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="acknowledgements", null=True
    )
    rich_text = RichTextField(
        null=True, blank=True, help_text=_("""Describe the acknowledgments.""")
    )


class AdditionalInformation(Orderable, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="additional_information",
        null=True,
    )
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_("""Free field for entering additional information or data."""),
    )


class DigitalPreservation(ClusterableModel, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="digital_preservation",
        null=True,
    )


class Ethics(ClusterableModel, RichTextWithLanguage, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="ethics", null=True
    )


class ArticleSubmissionFormatCheckList(
    ClusterableModel, RichTextWithLanguage, CommonControlField
):
    rich_text = RichTextField(
        _("Rich Text"),
        null=True,
        blank=True,
        help_text=_("Descreva o teim do check list"),
    )

    def __str__(self):
        remove_tags = re.compile("<.*?>")
        return re.sub(remove_tags, "", self.rich_text)


class ThematicAreaJournal(Orderable, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="thematic_area", null=True
    )
    thematic_area = models.ForeignKey(
        ThematicArea, on_delete=models.SET_NULL, blank=True, null=True
    )


class DigitalPreservationAgency(CommonControlField):
    name = models.TextField(
        verbose_name=_("Name"),
        blank=True,
        null=True,
    )
    acronym = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_("Acronym"),
    )
    url = models.URLField(
        blank=True,
        null=True,
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    class Meta:
        verbose_name = "Digitial Preservation Agency"
        verbose_name_plural = "Digital Preservation Agencies"
        unique_together = [
            (
                "name",
                "acronym",
                "url",
            )
        ]
        indexes = [
            models.Index(
                fields=[
                    "name",
                ]
            ),
            models.Index(
                fields=[
                    "url",
                ]
            ),
        ]

    @classmethod
    def load(cls, user):
        with open(
            "./journal/fixture/digital_preservation_agencies.csv", "r"
        ) as csvfile:
            digital_pa = csv.DictReader(
                csvfile, fieldnames=["name", "acronym", "url"], delimiter=";"
            )
            next(digital_pa)
            for row in digital_pa:
                logging.info(row)
                cls.create_or_update(
                    name=row["name"],
                    acronym=row["acronym"],
                    url=row["url"],
                    user=user,
                )

    @classmethod
    def get(
        cls,
        name,
        url,
        acronym,
    ):
        if not name or not url:
            raise ValueError(
                "DigitalPreservationAgency.get requires name or url parameter"
            )
        return cls.objects.get(name=name, url=url, acronym=acronym)

    @classmethod
    def create(
        cls,
        user,
        name,
        acronym,
        url,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.acronym = acronym or obj.acronym
            obj.name = name or obj.name
            obj.url = url or obj.url
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(name=name, url=url, acronym=acronym)

    @classmethod
    def create_or_update(
        cls,
        user,
        name,
        acronym,
        url,
    ):
        try:
            return cls.get(name=name, acronym=acronym, url=url)
        except cls.DoesNotExist:
            return cls.create(user, name, acronym, url)

    def __str__(self):
        return f"{self.name} ({self.acronym}) | {self.url}"


class SciELOJournal(CommonControlField, ClusterableModel, SocialNetwork):
    """
    A class used to represent a journal model designed in the SciELO context.

    Attributes
    ----------
    official : official journal class object
        journal model that contains only official data registered in the ISSN.

    Methods
    -------
    TODO
    """

    collection = models.ForeignKey(
        Collection,
        verbose_name=_("Collection"),
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    journal = models.ForeignKey(
        Journal,
        verbose_name=_("Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    journal_acron = models.TextField(_("Journal Acronym"), null=True, blank=True)
    issn_scielo = models.CharField(
        _("ISSN SciELO"), max_length=9, null=True, blank=True
    )
    status = models.CharField(
        _("Status"), max_length=12, choices=choices.STATUS, null=True, blank=True
    )

    autocomplete_search_field = "journal_acron"
    
    def autocomplete_label(self):
        return str(self)

    class Meta:
        ordering = ["journal__title"]

        verbose_name = _("SciELO Journal")
        verbose_name_plural = _("SciELO Journals")
        indexes = [
            models.Index(
                fields=[
                    "collection",
                    "journal_acron",
                ]
            ),
            models.Index(
                fields=[
                    "collection",
                    "issn_scielo",
                ]
            ),
        ]

    def __unicode__(self):
        return f"{self.collection} {self.journal_acron or self.issn_scielo}"

    def __str__(self):
        return f"{self.collection} {self.journal_acron or self.issn_scielo}"

    base_form_class = CoreAdminModelForm

    panels = [
        AutocompletePanel("journal"),
        FieldPanel("journal_acron"),
        FieldPanel("issn_scielo"),
        FieldPanel("status"),
        AutocompletePanel("collection"),
        InlinePanel("journal_history", label=_("Journal History"), classname="collapsed"),
    ]
    
    edit_handler = TabbedInterface( 
        [
            ObjectList(panels, heading="SciELO Journal"),
        ]
    )

    @classmethod
    def get(
        cls,
        collection,
        issn_scielo=None,
        journal_acron=None,
    ):
        if not collection:
            raise SciELOJournalGetError(
                "SciELOJournal.get requires collection parameter"
            )
        if issn_scielo:
            return cls.objects.get(collection=collection, issn_scielo=issn_scielo)
        if journal_acron:
            return cls.objects.get(collection=collection, journal_acron=journal_acron)
        raise SciELOJournalGetError(
            "SciELOJournal.get requires issn_scielo or journal_acron parameter"
        )

    @classmethod
    def create_or_update(
        cls,
        user,
        collection,
        issn_scielo=None,
        journal_acron=None,
        journal=None,
        code_status=None,
    ):
        try:
            obj = cls.get(
                collection, issn_scielo=issn_scielo, journal_acron=journal_acron
            )
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
        except (SciELOJournalGetError, cls.MultipleObjectsReturned) as e:
            raise SciELOJournalCreateOrUpdateError(
                _("Unable to create or update SciELO journal {}").format(e)
            )
        obj.issn_scielo = issn_scielo or obj.issn_scielo
        obj.journal_acron = journal_acron or obj.journal_acron
        obj.collection = collection or obj.collection
        obj.journal = journal or obj.journal
        obj.status = code_status or obj.status
        obj.save()
        return obj


class JournalParallelTitle(TextWithLang):
    official_journal = ParentalKey(
        OfficialJournal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="parallel_title",
    )

    panels = [
        FieldPanel("text"),
        AutocompletePanel("language"),
    ]

    def __unicode__(self):
        return "%s (%s)" % (self.text, self.language)

    def __str__(self):
        return "%s (%s)" % (self.text, self.language)

    @classmethod
    def create_or_update(cls, official_journal, text, language=None):
        if language:
            for item in official_journal.parallel_titles.filter(
                language=language
            ).iterator():
                item.delete()
                break
        obj = cls()
        obj.official_journal = official_journal
        obj.text = text
        obj.language = language
        obj.save()


class SubjectDescriptor(CommonControlField):
    value = models.CharField(max_length=255, null=True, blank=True, unique=True)

    autocomplete_search_field = "value"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.value}"

    class Meta:
        ordering = ["value"]

    @classmethod
    def get(
        cls,
        value,
        ):
        if not value:
            return None
        try:
            return cls.objects.get(value=value)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(value=value).first()

    @classmethod
    def create(
        cls,
        value,
        user,
    ):
        try:
            obj = cls(
                value=value,
                creator=user
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(value=value)

    @classmethod
    def get_or_create(
        cls,
        value,
        user,
        ):
        try:
            return cls.get(value=value)
        except cls.DoesNotExist:
            return cls.create(value=value, user=user)
        

class Subject(CommonControlField):
    code = models.CharField(max_length=30, null=True, blank=True)
    value = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.value}"

    @classmethod
    def load(cls, user):
        if not cls.objects.exists():
            for item in choices.STUDY_AREA:
                code, _ = item
                cls.create_or_update(
                    code=code,
                    user=user,
                )

    @classmethod
    def get(cls, code):
        if not code:
            raise ValueError("Subject.get requires code parameter")
        return cls.objects.get(code=code)

    @classmethod
    def create_or_update(
        cls,
        code,
        user,
    ):
        try:
            obj = cls.get(code=code)
        except cls.DoesNotExist:
            obj = cls()
            obj.code = code
            obj.creator = user
        except SubjectCreationOrUpdateError as e:
            raise SubjectCreationOrUpdateError(code=code, message=e)

        obj.value = dict(choices.STUDY_AREA).get(code) or obj.value
        obj.updated = user
        obj.save()
        return obj


class WebOfKnowledge(CommonControlField):
    code = models.CharField(max_length=8, null=True, blank=True)
    value = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.value}"

    @classmethod
    def load(cls, user):
        if not cls.objects.exists():
            for item in choices.WOS_DB:
                code, _ = item
                cls.create_or_update(code=code, user=user)

    @classmethod
    def get(cls, code):
        if not code:
            raise ValueError("WebOfKnowledge.get requires code parameter")
        return cls.objects.get(code=code)

    @classmethod
    def create_or_update(
        cls,
        code,
        user,
    ):
        try:
            obj = cls.get(code=code)
        except cls.DoesNotExist:
            obj = cls()
            obj.code = code
            obj.creator = user
        except WosdbCreationOrUpdateError as e:
            raise WosdbCreationOrUpdateError(code=code, message=e)

        obj.value = dict(choices.WOS_DB).get(code) or obj.value
        obj.updated_by = user
        obj.save()
        return obj


class WebOfKnowledgeSubjectCategory(CommonControlField):
    value = models.CharField(max_length=100, null=True, blank=True)

    autocomplete_search_field = "value"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.value}"

    @classmethod
    def load(cls, user):
        if not cls.objects.exists():
            with open("./journal/fixture/subjects_categories_wok.csv", "r") as fp:
                wos_area = fp.readlines()
            for value in wos_area:
                try:
                    cls.get_or_create(value=value.strip(), user=user)
                except Exception as e:
                    logging.exception(e)

    @classmethod
    def get_or_create(cls, value, user):
        try:
            obj = cls.objects.get(value=value)
        except cls.DoesNotExist:
            obj = cls()
            obj.creator = user
            obj.value = value
            obj.save()
        return obj

    class Meta:
        ordering = ["value"]


class Standard(CommonControlField):
    code = models.CharField(max_length=7, null=True, blank=True)
    value = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.value}"

    @classmethod
    def load(cls, user):
        if cls.objects.count() == 0:
            for item in choices.STANDARD:
                code, value = item
                cls.create_or_update(user, code=code, value=value)

    @classmethod
    def get(cls, code):
        if not code:
            raise ValueError("Standard.get requires code parameter")
        return cls.objects.get(code=code)

    @classmethod
    def create_or_update(
        cls,
        user,
        code,
        value=None,
    ):
        try:
            obj = cls.get(code=code)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.code = code
            obj.creator = user

        try:
            obj.value = value or dict(choices.STANDARD).get(code) or obj.value
        except Exception as e:
            pass

        try:
            obj.save()
        except Exception as e:
            raise StandardCreationOrUpdateError(
                f"Unable to create or update Standard {code} {value}. Exception: {type(e)} {e}"
            )
        return obj


class IndexedAt(CommonControlField):
    name = models.TextField(_("Name"), null=True, blank=False)
    acronym = models.TextField(_("Acronym"), null=True, blank=False)
    url = models.URLField(_("URL"), max_length=500, null=True, blank=False)
    description = models.TextField(_("Description"), null=True, blank=False)
    type = models.CharField(
        _("Type"), max_length=20, choices=choices.TYPE, null=True, blank=False
    )

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("name"),
        FieldPanel("acronym"),
        FieldPanel("url"),
        FieldPanel("description"),
        FieldPanel("type"),
    ]

    def __str__(self):
        return f"{self.acronym} - {self.name}"

    class Meta:
        ordering = ["name"]

    @classmethod
    def load(cls, user):
        with open("./journal/fixture/index_at.csv", "r") as csvfile:
            indexed_at = csv.DictReader(
                csvfile,
                fieldnames=["name", "acronym", "url", "type", "description"],
                delimiter=",",
            )
            for row in indexed_at:
                logging.info(row)
                cls.create_or_update(
                    name=row["name"],
                    acronym=row["acronym"],
                    url=row["url"],
                    type=row["type"],
                    description=row["description"],
                    user=user,
                )

    @classmethod
    def get(
        cls,
        name,
        acronym,
    ):
        if name:
            return cls.objects.get(name=name)
        if acronym:
            return cls.objects.get(acronym__iexact=acronym)
        raise Exception("IndexedAt.get requires name or acronym paramets")

    @classmethod
    def create_or_update(
        cls,
        user,
        name=None,
        acronym=None,
        description=None,
        url=None,
        type=None,
    ):
        try:
            obj = cls.get(name=name, acronym=acronym)
        except cls.DoesNotExist:
            obj = cls()
            obj.name = name
            obj.acronym = acronym
            obj.creator = user
        except IndexedAtCreationOrUpdateError as e:
            raise IndexedAtCreationOrUpdateError(name=name, acronym=acronym, message=e)

        obj.description = description or obj.description
        obj.url = url or obj.url
        obj.type = dict(choices.TYPE).get(type) if type else obj.type
        obj.updated_by = user
        obj.save()

        return obj


class IndexedAtFile(models.Model):
    attachment = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    is_valid = models.BooleanField(_("Is valid?"), default=False, blank=True, null=True)
    line_count = models.IntegerField(
        _("Number of lines"), default=0, blank=True, null=True
    )

    def filename(self):
        return os.path.basename(self.attachment.name)

    panels = [FieldPanel("attachment")]


class AdditionalIndexedAt(CommonControlField):
    name = models.TextField(_("Name"), null=True, blank=True)

    @classmethod
    def get(
        cls,
        name
        ):
        if name:
            try:
                return cls.objects.get(name=name)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(name=name).first()
        raise ValueError("AdditionalIndexedAt.get requires name paramenter")

    @classmethod
    def create(
        cls,
        name,
        user,
    ):
        obj = cls()
        obj.name = name
        obj.creator = user
        obj.save()
        return obj
        
    @classmethod
    def get_or_create(
        cls,
        name,
        user,
    ):
        try:
            return cls.get(name=name)
        except cls.DoesNotExist:
            return cls.create(name=name, user=user)

    autocomplete_search_field = "name"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.name}"


class Annotation(CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="annotation", null=True
    )
    notes = models.TextField(_("Notes"), blank=True, null=True)
    creation_date = models.DateField(_("Creation Date"), blank=True, null=True)
    update_date = models.DateField(_("Update Date"), blank=True, null=True)

    def __str__(self):
        return f"{self.notes} - {self.creation_date} - {self.update_date}"

    panels = [
        FieldPanel("notes"),
        FieldPanel("creation_date", read_only=True),
        FieldPanel("update_date", read_only=True),
    ]

    @classmethod
    def get(cls, notes, creation_date, update_date):
        if notes and creation_date and update_date:
            return cls.objects.get(
                notes=notes, creation_date=creation_date, update_date=update_date
            )
        raise ValueError(
            "Annotation.get requires notes, creation_date e update_date parameters"
        )

    @classmethod
    def create_or_update(
        cls,
        journal,
        notes,
        creation_date,
        update_date,
        user,
    ):
        try:
            annotation = cls.get(
                notes=notes, creation_date=creation_date, update_date=update_date
            )
        except cls.DoesNotExist:
            annotation = cls()
            annotation.creator = user

        annotation.journal = journal or annotation.journal
        annotation.notes = notes or annotation.notes
        annotation.updated_by = user
        annotation.save()
        return annotation


class JournalHistory(CommonControlField, Orderable):
    scielo_journal = ParentalKey(
        SciELOJournal,
        on_delete=models.SET_NULL,
        related_name="journal_history",
        null=True,
    )

    year = models.CharField(_("Event year"), max_length=4, null=True, blank=True)
    month = models.CharField(
        _("Event month"),
        max_length=2,
        choices=MONTHS,
        null=True,
        blank=True,
    )
    day = models.CharField(_("Event day"), max_length=2, null=True, blank=True)

    event_type = models.CharField(
        _("Event type"),
        null=True,
        blank=True,
        max_length=16,
        choices=choices.JOURNAL_EVENT_TYPE,
    )
    interruption_reason = models.CharField(
        _("Indexing interruption reason"),
        null=True,
        blank=True,
        max_length=16,
        choices=choices.INDEXING_INTERRUPTION_REASON,
    )

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("year"),
        FieldPanel("month"),
        FieldPanel("day"),
        FieldPanel("event_type"),
        FieldPanel("interruption_reason"),
    ]

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        indexes = [
            models.Index(
                fields=[
                    "event_type",
                ]
            ),
        ]

    @property
    def data(self):
        d = {
            "event_type": self.event_type,
            "interruption_reason": self.interruption_reason,
            "year": self.year,
            "month": self.month,
            "day": self.day,
        }

        return d

    def __str__(self):
        return f"{self.event_type} {self.interruption_reason} {self.year}/{self.month}/{self.day or '01'}"

    @classmethod
    def am_to_core(
        cls,
        scielo_journal,
        initial_year,
        initial_month,
        initial_day,
        final_year,
        final_month,
        final_day,
        event_type,
        interruption_reason,
    ):
        """
        Funcao para API article meta.
        Atualiza o Type Event de JournalHistory.
        """
        reasons = {
            None: "ceased",
            "not-open-access": "not-open-access",
            "suspended-by-committee": "by-committee",
            "suspended-by-editor": "by-editor",
        }
        try:
            obj = cls.objects.get(
                scielo_journal=scielo_journal,
                year=initial_year,
                month=initial_month,
                day=initial_day,
            )
        except cls.DoesNotExist:
            obj = cls()
            obj.scielo_journal = scielo_journal
            obj.year = initial_year
            obj.month = initial_month
            obj.day = initial_day
        obj.event_type = "ADMITTED"
        obj.save()

        if final_year and event_type:
            try:
                obj = cls.objects.get(
                    scielo_journal=scielo_journal,
                    year=final_year,
                    month=final_month,
                    day=final_day,
                )
            except cls.DoesNotExist:
                obj = cls()
                obj.scielo_journal = scielo_journal
                obj.year = final_year
                obj.month = final_month
                obj.day = final_day
            obj.event_type = "INTERRUPTED"
            obj.interruption_reason = reasons.get(interruption_reason)
            obj.save()


class AMJournal(CommonControlField):
    """
    Modelo que representa a coleta de dados de Journal na API Article Meta.

    from:
        https://articlemeta.scielo.org/api/v1/journal/?collection={collection}&issn={issn}"
    """

    collection = models.ForeignKey(
        Collection,
        verbose_name=_("Collection"),
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    scielo_issn = models.CharField(
        _("Scielo Issn"),
        max_length=9,
        blank=True,
        null=True,
    )
    data = models.JSONField(
        _("JSON File"),
        null=True,
        blank=True,
    )

    def __unicode__(self):
        return f"{self.scielo_issn} | {self.collection}"

    def __str__(self):
        return f"{self.scielo_issn} | {self.collection}"

    @classmethod
    def get(cls, scielo_issn, collection):
        if not scielo_issn and not collection:
            raise ValueError("Param scielo_issn and collection_acron3 is required")
        return cls.objects.get(scielo_issn=scielo_issn, collection=collection)

    @classmethod
    def create_or_update(cls, scielo_issn, collection, data, user):
        try:
            obj = cls.get(scielo_issn=scielo_issn, collection=collection)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls.objects.create()
            obj.creator = user
        except cls.MultipleObjectsReturned as e:
            raise (f"Error ao conseguir AMjournal {scielo_issn}: {e}")
        obj.collection = collection or obj.collection
        obj.scielo_issn = scielo_issn or obj.scielo_issn
        obj.data = data or obj.data
        obj.save()

        return obj


class TitleInDatabase(Orderable, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="title_in_database", null=True
    )
    indexed_at = models.ForeignKey(
        IndexedAt,
        on_delete=models.SET_NULL,
        verbose_name=_("Indexed At"),
        blank=True,
        null=True,
    )
    title = models.TextField(
        verbose_name=_("Title"),
        null=True,
        blank=True,
    )
    identifier = models.CharField(
        max_length=64,
        verbose_name=_("Identifier"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Title in Database")
        verbose_name_plural = _("Title in databases")
        unique_together = [
            (
                "journal",
                "indexed_at",
            )
        ]

    @classmethod
    def get(
        cls,
        journal,
        indexed_at,
    ):
        if not journal and not indexed_at:
            raise TitleInDatabaseCreationOrUpdateError(
                "TitleInDatabase.get requires journal, indexed_at e title parameter."
            )
        return cls.objects.get(
            journal=journal,
            indexed_at=indexed_at,
        )

    @classmethod
    def create(
        cls,
        user,
        journal,
        indexed_at=None,
        title=None,
        identifier=None,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.journal = journal
            obj.indexed_at = indexed_at or obj.indexed_at
            obj.title = title or obj.title
            obj.identifier = identifier or obj.identifier
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(
                journal=journal,
                indexed_at=indexed_at,
                title=title,
                identifier=identifier,
            )

    @classmethod
    def create_or_update(
        cls,
        user,
        journal,
        indexed_at,
        title,
        identifier,
    ):
        try:
            obj = cls.get(journal=journal, indexed_at=indexed_at)
            obj.title = title or obj.title
            obj.identifier = identifier or obj.identifier
            obj.updated_by = user
            obj.save()
            return obj
        except cls.DoesNotExist:
            return cls.create(
                user=user,
                journal=journal,
                indexed_at=indexed_at,
                title=title,
                identifier=identifier,
            )

    def __str__(self):
        return f"{self.indexed_at} | {self.title} | {self.identifier}"


class DataRepository(Orderable, CommonControlField):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="data_repository_uri",
        null=True,
    )
    uri = models.URLField(
        blank=True,
        null=True,
        help_text=_("Enter the URI of the data repository."),
    )


class JournalLogo(CommonControlField):
    journal = models.ForeignKey(
        Journal,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    logo = models.ForeignKey(
            "wagtailimages.Image",
            on_delete=models.SET_NULL,
            related_name="+",
            null=True,
            blank=True,
    )

    class Meta:
        unique_together = [("journal", "logo")]

    
    @classmethod
    def get(
        cls,
        journal,
        logo,
    ):
        if not journal and not logo:
            raise ValueError("JournalLogo.get requires journal and logo paramenters")
        return cls.objects.get(journal=journal, logo=logo)
    

    @classmethod
    def create(
        cls,
        journal,
        logo,
        user,
    ):
        try:
            obj = cls(
                journal=journal,
                logo=logo,
                creator=user,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(journal=journal, logo=logo)
        
    @classmethod
    def create_or_update(
        cls,
        journal,
        logo,
        user,
    ):
        try:
            return cls.get(journal=journal, logo=logo)
        except cls.DoesNotExist:
            return cls.create(journal=journal, logo=logo, user=user)
        

class JournalOtherTitle(CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="other_titles", null=True
    )
    title = models.TextField(null=True, blank=True)


    class Meta:
        unique_together = [("journal", "title")]


    @classmethod
    def get(
        cls,
        title,
        journal,
    ):
        if not title and not journal:
            raise ValueError("JournalTitle.get requires title paramenter")
        return journal.other_titles.get(title=title)
        
    @classmethod
    def create(
        cls,
        title,
        journal,
        user,
    ):
        try:
            obj = cls(
                title=title,
                journal=journal,
                creator=user,
            )
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(title=title, journal=journal)

    @classmethod
    def create_or_update(
        cls,
        title,
        journal,
        user,
    ):
        try:
            return cls.get(title=title, journal=journal)
        except cls.DoesNotExist:
            return cls.create(title=title, journal=journal, user=user)
    
    def __str__(self):
        return f"{self.title}"
