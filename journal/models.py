from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.core.models import Orderable
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel, TabbedInterface, ObjectList
from wagtail.images.edit_handlers import ImageChooserPanel

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

from core.models import CommonControlField, RichTextWithLang

from .forms import OfficialJournalForm, JournalForm
from . import choices

from institution.models import InstitutionHistory


class OfficialJournal(CommonControlField):
    """
    Class that represent the Official Journal
    """

    def __unicode__(self):
        return u'%s - %s' % (self.ISSNL, self.title) or ''

    def __str__(self):
        return u'%s - %s' % (self.ISSNL, self.title) or ''

    title = models.CharField(_('Official Title'), max_length=256, null=True, blank=True)
    foundation_year = models.CharField(_('Foundation Year'), max_length=4, null=True, blank=True)
    ISSN_print = models.CharField(_('ISSN Print'), max_length=9, null=True, blank=True)
    ISSN_electronic = models.CharField(_('ISSN Eletronic'), max_length=9, null=True, blank=True)
    ISSNL = models.CharField(_('ISSNL'), max_length=9, null=True, blank=True)

    @property
    def data(self):
        d = {
            "official_journal__title": self.title,
            "official_journal__foundation_year": self.foundation_year,
            "official_journal__ISSN_print": self.ISSN_print,
            "official_journal__ISSN_electronic": self.ISSN_electronic,
            "official_journal__ISSNL": self.ISSNL,
        }
        return d

    base_form_class = OfficialJournalForm


class SocialNetwork(models.Model):
    name = models.CharField(_('Name'), max_length=255, choices=choices.SOCIAL_NETWORK_NAMES,
                            null=True, blank=True)
    url = models.URLField(_('URL'), max_length=255, null=True, blank=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('url')
    ]

    class Meta:
        abstract = True


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
    official = models.ForeignKey(OfficialJournal, verbose_name=_('Official Journal'),
                                 null=True, blank=True, on_delete=models.SET_NULL)
    short_title = models.CharField(_('Short Title'), max_length=100, null=True, blank=True)
    logo = models.ForeignKey('wagtailimages.Image', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    submission_online_url = models.URLField(_("Submission online URL"), max_length=255, null=True, blank=True)

    panels_identification = [
        FieldPanel('official'),
        FieldPanel('short_title'),
    ]

    panels_title = [
        InlinePanel('title', label=_('SciELO Journal Title'), classname='collapsed'),
    ]

    panels_mission = [
        InlinePanel('mission', label=_('Mission'), classname="collapsed"),
    ]

    panels_owner = [
        InlinePanel('owner', label=_('Owner'), classname="collapsed"),
    ]

    panels_editorial_manager = [
        InlinePanel('editorialmanager', label=_('Editorial Manager'), classname="collapsed"),
    ]

    panels_publisher = [
        InlinePanel('publisher', label=_('Publisher'), classname="collapsed"),
    ]

    panels_sponsor = [
        InlinePanel('sponsor', label=_('Sponsor'), classname="collapsed"),
    ]

    panels_website = [
        ImageChooserPanel('logo', heading=_('Logo')),
        FieldPanel('submission_online_url'),
        InlinePanel('journalsocialnetwork', label=_('Social Network'))
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_identification, heading=_('Identification')),
            ObjectList(panels_title, heading=_('Title')),
            ObjectList(panels_mission, heading=_('Missions')),
            ObjectList(panels_owner, heading=_('Owners')),
            ObjectList(panels_editorial_manager, heading=_('Editorial Manager')),
            ObjectList(panels_publisher, heading=_('Publisher')),
            ObjectList(panels_sponsor, heading=_('Sponsor')),
            ObjectList(panels_website, heading=_('Website')),
        ]
    )

    class Meta:
        verbose_name = _('SciELO Journal')
        verbose_name_plural = _('SciELO Journals')
        indexes = [
            models.Index(fields=['official', ]),
            models.Index(fields=['short_title', ]),
        ]

    @property
    def data(self):
        d = {}  # this dictionary will come in handy when new attributes are added

        if self.official:
            d.update(self.official.data)

        return d

    def __unicode__(self):
        return u'%s' % self.official or ''

    def __str__(self):
        return u'%s' % self.official or ''

    base_form_class = JournalForm


class ScieloJournalTitle(Orderable):
    page = ParentalKey(ScieloJournal, related_name='title')
    journal_title = models.CharField(_('SciELO Journal Title'), max_length=255, null=True, blank=True)


class Mission(Orderable, RichTextWithLang):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name='mission')


class Owner(Orderable, InstitutionHistory):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name='owner')


class EditorialManager(Orderable, InstitutionHistory):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name='editorialmanager')


class Publisher(Orderable, InstitutionHistory):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name='publisher')


class Sponsor(Orderable, InstitutionHistory):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name='sponsor')


class JournalSocialNetwork(Orderable, SocialNetwork):
    page = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name='journalsocialnetwork')
