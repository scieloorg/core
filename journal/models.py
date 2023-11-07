import os

from django.contrib.auth import get_user_model
from django.db import models
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
    RichTextWithLang,
    TextWithLang,
)
from institution.models import (
    CopyrightHolderHistoryItem,
    EditorialManagerHistoryItem,
    OwnerHistoryItem,
    PublisherHistoryItem,
    SponsorHistoryItem,
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
)
from reference.models import JournalTitle
from vocabulary.models import Vocabulary

from . import choices

User = get_user_model()


class OfficialJournal(CommonControlField):
    """
    Class that represent the Official Journal
    """

    title = models.TextField(_("Official Title"), null=True, blank=True)
    iso_short_title = models.TextField(_("ISO Short Title"), null=True, blank=True)
    parallel_titles = models.ManyToManyField(
        "JournalParallelTitles", null=True, blank=True
    )
    new_title = models.ForeignKey(
        "self",
        verbose_name=_("New Title"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_title_journal",
    )
    old_title = models.ForeignKey(
        "self",
        verbose_name=_("Old Title"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="old_title_journal",
    )
    foundation_year = models.CharField(
        _("Foundation Year"), max_length=4, null=True, blank=True
    )
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
        _("Terminate year"), max_length=4, null=True, blank=True
    )
    terminate_month = models.CharField(
        _("Terminate month"), max_length=2, choices=MONTHS, null=True, blank=True
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
    issnl = models.CharField(_("ISSNL"), max_length=9, null=True, blank=True)

    panels_titles = [
        FieldPanel("title"),
        FieldPanel("iso_short_title"),
        AutocompletePanel("parallel_titles"),
        FieldPanel("old_title"),
        FieldPanel("new_title"),
    ]

    panels_dates = [
        FieldPanel("foundation_year"),
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

    class Meta:
        verbose_name = _("Official Journal")
        verbose_name_plural = _("Official Journals")
        indexes = [
            models.Index(
                fields=[
                    "title",
                ]
            ),
            models.Index(
                fields=[
                    "foundation_year",
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

    def __unicode__(self):
        return "%s - %s" % (self.issnl, self.title) or ""

    def __str__(self):
        return "%s - %s" % (self.issnl, self.title) or ""

    @property
    def data(self):
        d = {
            "official_journal__title": self.title,
            "official_journal__foundation_year": self.foundation_year,
            "official_journal__issn_print": self.issn_print,
            "official_journal__issn_electronic": self.issn_electronic,
            "official_journal__issnl": self.issnl,
        }
        return d

    @classmethod
    def get(cls, issn_print=None, issn_electronic=None, issnl=None):
        if issn_electronic:
            return cls.objects.get(issn_electronic=issn_electronic)
        if issn_print:
            return cls.objects.get(issn_print=issn_print)
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
        foundation_year=None,
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
        obj.foundation_year = foundation_year or obj.foundation_year
        obj.title = title or obj.title
        obj.save()

        return obj

    base_form_class = CoreAdminModelForm


class SocialNetwork(models.Model):
    name = models.TextField(
        _("Name"), choices=choices.SOCIAL_NETWORK_NAMES, null=True, blank=True
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
        verbose_name=_("Official Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    title = models.TextField(_("Journal Title"), null=True, blank=True)
    short_title = models.TextField(_("Short Title"), null=True, blank=True)
    other_titles = models.ManyToManyField(JournalTitle, verbose_name=_("Other titles"))
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
    collection_main_url = models.URLField(
        _("Collection Main Url"),
        null=True,
        blank=True,
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
    )
    subject = models.ManyToManyField(
        "Subject",
        verbose_name=_("Study Areas"),
    )
    wos_db = models.ManyToManyField(
        "WebOfKnowledge",
        verbose_name=_("Web of Knowledge Databases"),
    )
    wos_area = models.ManyToManyField(
        "WebOfKnowledgeSubjectCategory",
        verbose_name=_("Web of Knowledge Subject Categories"),
    )
    text_language = models.ManyToManyField(
        Language,
        verbose_name=_("Text Languages"),
        related_name="text_language",
    )
    abstract_language = models.ManyToManyField(
        Language,
        verbose_name=_("Abstract Languages"),
        related_name="abstract_language",
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
    )
    secs_code = models.TextField(
        _("Secs Code"),
        null=True,
        blank=True,
    )
    medline_code = models.TextField(
        _("Medline Code"),
        null=True,
        blank=True,
    )
    medline_short_title = models.TextField(
        _("Medline Code"),
        null=True,
        blank=True,
    )  # (no xml é abbrev-journal-title do tipo nlm-title)
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
        max_length=50,
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

    panels_titles = [
        AutocompletePanel("official"),
        FieldPanel("title"),
        FieldPanel("short_title"),
        AutocompletePanel("other_titles"),
    ]

    panels_scope_and_about = [
        InlinePanel("mission", label=_("Mission"), classname="collapsed"),
        InlinePanel("history", label=_("Brief History"), classname="collapsed"),
        InlinePanel("focus", label=_("Focus and Scope"), classname="collapsed"),
        FieldPanel("subject_descriptor"),
        FieldPanel("subject"),
        FieldPanel("wos_db"),
        FieldPanel("wos_area"),
    ]

    panels_formal_information = [
        FieldPanel("frequency"),
        FieldPanel("publishing_model"),
        FieldPanel("text_language"),
        FieldPanel("abstract_language"),
        FieldPanel("standard"),
        AutocompletePanel("vocabulary"),
        FieldPanel("alphabet"),
        FieldPanel("classification"),
        FieldPanel("national_code"),
        FieldPanel("type_of_literature"),
        FieldPanel("treatment_level"),
        FieldPanel("level_of_publication"),
    ]

    panels_interoperation = [
        FieldPanel("secs_code"),
        FieldPanel("medline_code"),
        FieldPanel("medline_short_title"),
        FieldPanel("indexed_at"),
    ]

    panels_institutions = [
        InlinePanel("owner_history", label=_("Owner"), classname="collapsed"),
        InlinePanel(
            "editorialmanager_history",
            label=_("Editorial Manager"),
            classname="collapsed",
        ),
        InlinePanel("publisher_history", label=_("Publisher"), classname="collapsed"),
        InlinePanel("sponsor_history", label=_("Sponsor"), classname="collapsed"),
        InlinePanel(
            "copyright_holder_history",
            label=_("Copyright Holder"),
            classname="collapsed",
        ),
    ]

    panels_website = [
        FieldPanel("logo", heading=_("Logo")),
        FieldPanel("journal_url"),
        FieldPanel("submission_online_url"),
        FieldPanel("collection_main_url"),
        InlinePanel("journalsocialnetwork", label=_("Social Network")),
    ]

    panels_open_science = [
        FieldPanel("open_access"),
        FieldPanel("url_oa"),
        AutocompletePanel("use_license"),
    ]

    panels_policy = [
        InlinePanel("open_data", label=_("Open data"), classname="collapsed"),
        InlinePanel("preprint", label=_("Preprint"), classname="collapsed"),
        InlinePanel("review", label=_("Peer review"), classname="collapsed"),
        InlinePanel("ecommittee", label=_("Ethics Committee"), classname="collapsed"),
        InlinePanel("copyright", label=_("Copyright"), classname="collapsed"),
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
        InlinePanel(
            "conflict_policy",
            label=_("Conflict of interest policy"),
            classname="collapsed",
        ),
    ]
    panels_notes = [InlinePanel("annotation", label=_("Notes"), classname="collapsed")]

    panels_legacy_compatibility_fields = [
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

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_titles, heading=_("Titles")),
            ObjectList(panels_scope_and_about, heading=_("Scope and about")),
            ObjectList(panels_interoperation, heading=_("Interoperation")),
            ObjectList(panels_formal_information, heading=_("Formal information")),
            ObjectList(panels_institutions, heading=_("Related Institutions")),
            ObjectList(panels_website, heading=_("Website")),
            ObjectList(panels_open_science, heading=_("Open Science")),
            ObjectList(panels_policy, heading=_("Journal Policy")),
            ObjectList(panels_notes, heading=_("Notes")),
            ObjectList(
                panels_legacy_compatibility_fields, heading=_("Legacy Compatibility")
            ),
        ]
    )

    class Meta:
        verbose_name = _("Journal")
        verbose_name_plural = _("Journals")
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
        ]

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
        other_titles=None,
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

        if other_titles:
            obj.other_titles.set(other_titles)

        return obj

    def __unicode__(self):
        return "%s" % self.official or ""

    def __str__(self):
        return "%s" % self.official or ""

    base_form_class = CoreAdminModelForm


class Mission(Orderable, RichTextWithLang, CommonControlField):
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


class OwnerHistory(Orderable, OwnerHistoryItem):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="owner_history", null=True
    )


class EditorialManagerHistory(Orderable, EditorialManagerHistoryItem):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="editorialmanager_history",
        null=True,
    )


class PublisherHistory(Orderable, PublisherHistoryItem):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="publisher_history", null=True
    )


class SponsorHistory(Orderable, SponsorHistoryItem):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, null=True, related_name="sponsor_history"
    )


class CopyrightHolderHistory(Orderable, CopyrightHolderHistoryItem):
    journal = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        null=True,
        related_name="copyright_holder_history",
    )


class JournalSocialNetwork(Orderable, SocialNetwork):
    page = ParentalKey(
        Journal,
        on_delete=models.SET_NULL,
        related_name="journalsocialnetwork",
        null=True,
    )


class OpenData(Orderable, RichTextWithLang, CommonControlField):
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


class Preprint(Orderable, RichTextWithLang, CommonControlField):
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


class History(Orderable, RichTextWithLang, CommonControlField):
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


class Focus(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_("Insert here the focus and scope of the journal"),
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="focus", null=True
    )


class Review(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(
        null=True, blank=True, help_text=_("Brief description of the review flow")
    )
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="review", null=True
    )


class Ecommittee(Orderable, RichTextWithLang, CommonControlField):
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


class Copyright(Orderable, RichTextWithLang, CommonControlField):
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


class WebsiteResponsibility(Orderable, RichTextWithLang, CommonControlField):
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


class AuthorResponsibility(Orderable, RichTextWithLang, CommonControlField):
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


class Policies(Orderable, RichTextWithLang, CommonControlField):
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


class ConflictPolicy(Orderable, RichTextWithLang, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.SET_NULL, related_name="conflict_policy", null=True
    )


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

    journal_history = models.ManyToManyField(
        "JournalHistory",
        verbose_name=_("Journal History"),
    )

    autocomplete_search_field = "journal_acron"

    def autocomplete_label(self):
        return str(self)

    class Meta:
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
        AutocompletePanel("journal_history"),
    ]

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


class JournalParallelTitles(TextWithLang):
    autocomplete_search_field = "text"

    def autocomplete_label(self):
        return str(self)

    def __unicode__(self):
        return "%s (%s)" % (self.text, self.language)

    def __str__(self):
        return "%s (%s)" % (self.text, self.language)


class SubjectDescriptor(CommonControlField):
    value = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.value}"


class Subject(CommonControlField):
    code = models.CharField(max_length=30, null=True, blank=True)
    value = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.value}"

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

    def __str__(self):
        return f"{self.value}"


class Standard(CommonControlField):
    code = models.CharField(max_length=7, null=True, blank=True)
    value = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} - {self.value}"

    @classmethod
    def load(cls, user, items):
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
                f"Unable to create or update Standard {code} {value}. Exception: {type(e)} {e}")
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

    @classmethod
    def get(
        cls,
        name,
        acronym,
    ):
        if name:
            return cls.objects.get(name=name)
        if acronym:
            return cls.objects.get(acronym)
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
        obj.type = type or obj.type
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
        FieldPanel("creation_date", classname="myReadonlyInput"),
        FieldPanel("update_date", classname="myReadonlyInput"),
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


class JournalHistory(CommonControlField):
    initial_year = models.CharField(
        _("Initial Occurrence date year"), max_length=4, null=True, blank=True
    )
    initial_month = models.CharField(
        _("Initial Occurrence date month"),
        max_length=2,
        choices=MONTHS,
        null=True,
        blank=True,
    )
    initial_day = models.CharField(
        _("Initial Occurrence date day"), max_length=2, null=True, blank=True
    )
    final_year = models.CharField(
        _("Final Occurrence date year"), max_length=4, null=True, blank=True
    )
    final_month = models.CharField(
        _("Final Occurrence date month"),
        max_length=2,
        choices=MONTHS,
        null=True,
        blank=True,
    )
    final_day = models.CharField(
        _("Final Occurrence date day"), max_length=2, null=True, blank=True
    )
    occurrence_type = models.TextField(
        _("Occurrence type"),
        null=True,
        blank=True,
    )

    autocomplete_search_field = "occurrence_type"

    def autocomplete_label(self):
        return str(self)

    panels = [
        FieldPanel("initial_year"),
        FieldPanel("initial_month"),
        FieldPanel("initial_day"),
        FieldPanel("final_year"),
        FieldPanel("final_month"),
        FieldPanel("final_day"),
        FieldPanel("occurrence_type"),
    ]

    class Meta:
        verbose_name = _("Event")
        verbose_name_plural = _("Events")
        indexes = [
            models.Index(
                fields=[
                    "occurrence_type",
                ]
            ),
        ]

    @property
    def data(self):
        d = {
            "occurrence_type": self.occurrence_type,
            "initial_year": self.initial_year,
            "initial_month": self.initial_month,
            "initial_day": self.initial_day,
            "final_year": self.final_year,
            "final_month": self.final_month,
            "final_day": self.final_day,
        }

        return d

    def __str__(self):
        return "%s from %s/%s/%s to %s/%s/%s" % (
            self.occurrence_type,
            self.initial_year,
            self.initial_month,
            self.initial_day or "00",
            self.final_year,
            self.final_month,
            self.final_day or "00",
        )

    base_form_class = CoreAdminModelForm
