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
    def get_or_create(
        cls, title, foundation_year, issn_print, issn_electronic, issnl, user
    ):  
        if issnl:
            official_journals = cls.objects.filter(issnl=issnl)
        else:
            official_journals = cls.objects.filter(title=title)
        try:
            official_journal = official_journals[0]
        except IndexError:
            official_journal = cls()
            official_journal.issnl = issnl
            official_journal.title = title
            official_journal.issn_print = issn_print
            official_journal.issn_electronic = issn_electronic
            official_journal.foundation_year = foundation_year
            official_journal.creator = user
            official_journal.save()

        return official_journal

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


class ScieloJournal(CommonControlField, ClusterableModel, SocialNetwork):
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
    issn_scielo = models.CharField(
        _("ISSN SciELO"), max_length=9, null=True, blank=True
    )
    title = models.TextField(_("SciELO Journal Title"), null=True, blank=True)
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

    collection = models.ForeignKey(
        Collection,
        verbose_name=_("Collection"),
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
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
        help_text=mark_safe(_("""Suggested form: <a target='_blank' href='https://wp.scielo.org/wp-content/uploads/Formulario-de-Conformidade-Ciencia-Aberta.docx'>https://wp.scielo.org/wp-content/uploads/Formulario-de-Conformidade-Ciencia-Aberta.docx</a>""")),
    )

    panels_identification = [
        FieldPanel("official"),
        FieldPanel("title"),
        FieldPanel("short_title"),
        FieldPanel("collection"),
    ]

    panels_mission = [
        InlinePanel("mission", label=_("Mission"), classname="collapsed"),
    ]

    panels_institutions = [
        InlinePanel("owner", label=_("Owner"), classname="collapsed"),
        InlinePanel("editorialmanager", label=_("Editorial Manager"), classname="collapsed"),
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
        InlinePanel("website_responsibility", label=_("Intellectual Property / Terms of use / Website responsibility"), classname="collapsed"),
        InlinePanel("author_responsibility", label=_("Intellectual Property / Terms of use / Author responsibility"), classname="collapsed"),
        InlinePanel("policies", label=_("Retraction Policy | Ethics and Misconduct Policy"), classname="collapsed"),
        InlinePanel("conflict_policy", label=_("Conflict of interest policy"), classname="collapsed"),
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
        verbose_name = _("SciELO Journal")
        verbose_name_plural = _("SciELO Journals")
        indexes = [
            models.Index(
                fields=[
                    "issn_scielo",
                ]
            ),
            models.Index(
                fields=[
                    "title",
                ]
            ),
            models.Index(
                fields=[
                    "short_title",
                ]
            ),
            models.Index(
                fields=[
                    "submission_online_url",
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
                "scielo_journal__issn_scielo": self.issn_scielo,
                "scielo_journal__title": self.title,
                "scielo_journal__short_title": self.short_title,
                "scielo_journal__submission_online_url": self.submission_online_url,
            }
        )

        return d

    @classmethod
    def get_or_create(
        cls, 
        official_journal, 
        issn_scielo, 
        title, 
        short_title, 
        submission_online_url, 
        open_access,
        collection, 
        user
    ):
        scielo_journals = cls.objects.filter(official=official_journal)
        try:
            scielo_journal = scielo_journals[0]
        except IndexError:
            scielo_journal = cls()
            scielo_journal.official = official_journal
            scielo_journal.issn_scielo = issn_scielo
            scielo_journal.title = title
            scielo_journal.short_title = short_title
            scielo_journal.creator = user
            scielo_journal.submission_online_url = submission_online_url
            scielo_journal.open_access = open_access
            scielo_journal.collection = collection
            scielo_journal.save()
        return scielo_journal

    def __unicode__(self):
        return "%s" % self.official or ""

    def __str__(self):
        return "%s" % self.official or ""

    base_form_class = CoreAdminModelForm


class Mission(Orderable, RichTextWithLang, CommonControlField):
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="mission"
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
    def get_or_create(cls, scielo_journal, scielo_issn, mission_rich_text, language, user):
        scielo_missions = cls.objects.filter(
            journal__official__issnl=scielo_issn, language=language
        )
        try:
            scielo_mission = scielo_missions[0]
        except IndexError:
            scielo_mission = cls()
            scielo_mission.rich_text = mission_rich_text
            scielo_mission.language = language
            scielo_mission.journal = scielo_journal
            scielo_mission.creator = user
            scielo_mission.save()

        return scielo_mission


class Owner(Orderable, InstitutionHistory):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name="owner")


class EditorialManager(Orderable, InstitutionHistory):
    page = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="editorialmanager"
    )


class Publisher(Orderable, InstitutionHistory):
    page = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="publisher"
    )


class Sponsor(Orderable, InstitutionHistory):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name="sponsor")


class JournalSocialNetwork(Orderable, SocialNetwork):
    page = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="journalsocialnetwork"
    )


class OpenData(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True, 
            help_text=mark_safe(_("""Refers to sharing data, codes, methods and other materials used and 
            resulting from research that are usually the basis of the texts of articles published by journals. 
            Guide: <a target='_blank' href='https://wp.scielo.org/wp-content/uploads/Guia_TOP_pt.pdf'>https://wp.scielo.org/wp-content/uploads/Guia_TOP_pt.pdf</a>""")))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="open_data"
    )


class Preprint(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True, 
            help_text=_("""A preprint is defined as a manuscript ready for submission to a journal that is deposited 
            with trusted preprint servers before or in parallel with submission to a journal. 
            This practice joins that of continuous publication as mechanisms to speed up research communication. 
            Preprints share with journals the originality in the publication of articles and inhibit the use of 
            the double-blind procedure in the evaluation of manuscripts. 
            The use of preprints is an option and choice of the authors and it is up to the journals to adapt 
            their policies to accept the submission of manuscripts previously deposited in a preprints server 
            recognized by the journal."""))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="preprint"
    )

    
class History(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True, 
            help_text=_("Insert here a brief history with events and milestones in the trajectory of the journal"))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="history"
    )


class Focus(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True,
            help_text=_("Insert here the focus and scope of the journal"))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="focus"
    )


class Review(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True,
            help_text=_("Brief description of the review flow"))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="review"
    )


class Ecommittee(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True,
            help_text=_("""Authors must attach a statement of approval from the ethics committee of 
            the institution responsible for approving the research"""))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="ecommittee"
    )


class Copyright(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True,
            help_text=_("""Describe the policy used by the journal on copyright issues. 
            We recommend that this section be in accordance with the recommendations of the SciELO criteria, 
            item 5.2.10.1.2. - Copyright"""))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="copyright"
    )


class WebsiteResponsibility(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True,
            help_text=_("""EX. DOAJ: Copyright terms applied to posted content must be clearly stated and separate 
            from copyright terms applied to the website"""))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="website_responsibility"
    )


class AuthorResponsibility(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True, 
            help_text=_("""The author's declaration of responsibility for the content published in 
            the journal that owns the copyright Ex. DOAJ: The terms of copyright must not contradict 
            the terms of the license or the terms of the open access policy. "All rights reserved" is 
            never appropriate for open access content"""))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="author_responsibility"
    )


class Policies(Orderable, RichTextWithLang, CommonControlField):
    rich_text = RichTextField(null=True, blank=True,
            help_text=mark_safe(_("""Describe here how the journal will deal with ethical issues and/or 
            issues that may damage the journal's reputation. What is the journal's position regarding 
            the retraction policy that the journal will adopt in cases of misconduct. 
            Best practice guide: <a target='_blank' 
            href='https://wp.scielo.org/wp-content/uploads/Guia-de-Boas-Praticas-para-o-Fortalecimento-da-Etica-na-Publicacao-Cientifica.pdf'>
            https://wp.scielo.org/wp-content/uploads/Guia-de-Boas-Praticas-para-o-Fortalecimento-da-Etica-na-Publicacao-Cientifica.pdf</a>""")))
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="policies"
    )


class ConflictPolicy(Orderable, RichTextWithLang, CommonControlField):
    journal = ParentalKey(
        ScieloJournal, on_delete=models.CASCADE, related_name="conflict_policy"
    )
