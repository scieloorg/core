from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.models import Orderable
from wagtail.fields import RichTextField

from collection.models import Collection
from core.forms import CoreAdminModelForm
from core.models import CommonControlField, RichTextWithLang
from institution.models import InstitutionHistory
from journal.exceptions import (
    MissionCreateOrUpdateError,
    MissionGetError,
    JournalCreateOrUpdateError,
    JournalGetError,
    OfficialJournalCreateOrUpdateError,
    OfficialJournalGetError,
    SciELOJournalCreateOrUpdateError,
    SciELOJournalGetError,
)
from . import choices


class OfficialJournal(CommonControlField):
    """
    Class that represent the Official Journal
    """

    title = models.TextField(_("Official Title"), null=True, blank=True)
    foundation_year = models.CharField(
        _("Foundation Year"), max_length=4, null=True, blank=True
    )
    issn_print = models.CharField(_("ISSN Print"), max_length=9, null=True, blank=True)
    issn_electronic = models.CharField(
        _("ISSN Eletronic"), max_length=9, null=True, blank=True
    )
    issnl = models.CharField(_("ISSNL"), max_length=9, null=True, blank=True)

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


class Journal(CommonControlField, ClusterableModel, SocialNetwork):
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

    collection = models.ManyToManyField(
        Collection,
        verbose_name=_("Collection"),
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

    panels_identification = [
        FieldPanel("official"),
        FieldPanel("title"),
        FieldPanel("short_title"),
        InlinePanel("collection"),
    ]

    panels_mission = [
        InlinePanel("mission", label=_("Mission"), classname="collapsed"),
    ]

    panels_institutions = [
        InlinePanel("owner", label=_("Owner"), classname="collapsed"),
        InlinePanel(
            "editorialmanager", label=_("Editorial Manager"), classname="collapsed"
        ),
        InlinePanel("publisher", label=_("Publisher"), classname="collapsed"),
        InlinePanel("sponsor", label=_("Sponsor"), classname="collapsed"),
    ]

    panels_website = [
        FieldPanel("logo", heading=_("Logo")),
        FieldPanel("submission_online_url"),
        InlinePanel("journalsocialnetwork", label=_("Social Network")),
    ]

    panels_about = [
        InlinePanel("history", label=_("Brief History"), classname="collapsed"),
        InlinePanel("focus", label=_("Focus and Scope"), classname="collapsed"),
    ]

    panels_open_science = [
        FieldPanel("open_access"),
        FieldPanel("url_oa"),
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

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_identification, heading=_("Identification")),
            ObjectList(panels_mission, heading=_("Missions")),
            ObjectList(panels_institutions, heading=_("Related Institutions")),
            ObjectList(panels_website, heading=_("Website")),
            ObjectList(panels_about, heading=_("About Journal")),
            ObjectList(panels_open_science, heading=_("Open Science")),
            ObjectList(panels_policy, heading=_("Journal Policy")),
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

        for scielo_j in SciELOJournal.objects.filter(journal=self):
            obj.collection.add(scielo_j.collection)
        obj.save()
        return obj

    def __unicode__(self):
        return "%s" % self.official or ""

    def __str__(self):
        return "%s" % self.official or ""

    base_form_class = CoreAdminModelForm


class Mission(Orderable, RichTextWithLang, CommonControlField):
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="mission")

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


class Owner(Orderable, InstitutionHistory):
    page = ParentalKey(Journal, on_delete=models.CASCADE, related_name="owner")


class EditorialManager(Orderable, InstitutionHistory):
    page = ParentalKey(
        Journal, on_delete=models.CASCADE, related_name="editorialmanager"
    )


class Publisher(Orderable, InstitutionHistory):
    page = ParentalKey(Journal, on_delete=models.CASCADE, related_name="publisher")


class Sponsor(Orderable, InstitutionHistory):
    page = ParentalKey(Journal, on_delete=models.CASCADE, related_name="sponsor")


class JournalSocialNetwork(Orderable, SocialNetwork):
    page = ParentalKey(
        Journal, on_delete=models.CASCADE, related_name="journalsocialnetwork"
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
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="open_data")


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
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="preprint")


class History(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            "Insert here a brief history with events and milestones in the trajectory of the journal"
        ),
    )
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="history")


class Focus(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_("Insert here the focus and scope of the journal"),
    )
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="focus")


class Review(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(
        null=True, blank=True, help_text=_("Brief description of the review flow")
    )
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="review")


class Ecommittee(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(
        null=True,
        blank=True,
        help_text=_(
            """Authors must attach a statement of approval from the ethics committee of 
            the institution responsible for approving the research"""
        ),
    )
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="ecommittee")


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
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="copyright")


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
        Journal, on_delete=models.CASCADE, related_name="website_responsibility"
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
        Journal, on_delete=models.CASCADE, related_name="author_responsibility"
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
    journal = ParentalKey(Journal, on_delete=models.CASCADE, related_name="policies")


class ConflictPolicy(Orderable, RichTextWithLang, CommonControlField):
    journal = ParentalKey(
        Journal, on_delete=models.CASCADE, related_name="conflict_policy"
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
    # TODO adicionar eventos de entrada e saída de coleção / refatorar journal_and_collection

    class Meta:
        verbose_name = _("SciELO Journal")
        verbose_name_plural = _("SciELO Journals")
        index_together = [
            ["collection", "journal_acron"],
            ["collection", "issn_scielo"],
        ]

    def __unicode__(self):
        return f"{self.collection} {self.journal_acron or self.issn_scielo}"

    def __str__(self):
        return f"{self.collection} {self.journal_acron or self.issn_scielo}"

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("journal"),
        FieldPanel("journal_acron"),
        FieldPanel("issn_scielo"),
        FieldPanel("collection"),
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
        obj.journal = journal or obj.journal
        obj.save()
        return obj
