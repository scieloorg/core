from django.db import models
from django.utils.translation import gettext_lazy as _

from wagtail.core.models import Orderable
from wagtail.admin.edit_handlers import FieldPanel, InlinePanel, TabbedInterface, ObjectList
from wagtail.images.edit_handlers import ImageChooserPanel

from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel

from core.models import CommonControlField, RichTextWithLang

from core.forms import CoreAdminModelForm
from . import choices

from institution.models import InstitutionHistory


class OfficialJournal(CommonControlField):
    """
    Class that represent the Official Journal
    """

    def __unicode__(self):
        return u'%s - %s' % (self.issnl, self.title) or ''

    def __str__(self):
        return u'%s - %s' % (self.issnl, self.title) or ''

    title = models.CharField(_('Official Title'), max_length=256, null=True, blank=True)
    foundation_year = models.CharField(_('Foundation Year'), max_length=4, null=True, blank=True)
    issn_print = models.CharField(_('ISSN Print'), max_length=9, null=True, blank=True)
    issn_electronic = models.CharField(_('ISSN Eletronic'), max_length=9, null=True, blank=True)
    issnl = models.CharField(_('ISSNL'), max_length=9, null=True, blank=True)

    class Meta:
        verbose_name = _('Official Journal')
        verbose_name_plural = _('Official Journals')
        indexes = [
            models.Index(fields=['title', ]),
            models.Index(fields=['foundation_year', ]),
            models.Index(fields=['issn_print', ]),
            models.Index(fields=['issn_electronic', ]),
            models.Index(fields=['issnl', ]),
        ]

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
    def get_or_create(cls, title, foundation_year, issn_print, issn_electronic, issnl, user):
        official_journals = cls.objects.filter(issnl=issnl)
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
    name = models.CharField(_('Name'), max_length=255, choices=choices.SOCIAL_NETWORK_NAMES,
                            null=True, blank=True)
    url = models.URLField(_('URL'), max_length=255, null=True, blank=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('url')
    ]

    class Meta:
        verbose_name = _('Social Network')
        verbose_name_plural = _('Social Networks')
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['url', ]),
        ]
        abstract = True

    @property
    def data(self):
        d = {
            'social_network__name': self.name,
            'social_network__url': self.url
        }

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
    official = models.ForeignKey(OfficialJournal, verbose_name=_('Official Journal'),
                                 null=True, blank=True, on_delete=models.SET_NULL)
    issn_scielo = models.CharField(_('ISSN SciELO'), max_length=9, null=True, blank=True)
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
            models.Index(fields=['issn_scielo', ]),
            models.Index(fields=['short_title', ]),
            models.Index(fields=['submission_online_url', ]),
        ]

    @property
    def data(self):
        d = {}

        if self.official:
            d.update(self.official.data)

        d.update({
                'scielo_journal__issn_scielo': self.issn_scielo,
                'scielo_journal__short_title': self.short_title,
                'scielo_journal__submission_online_url': self.submission_online_url
            })

        return d

    @classmethod
    def get_or_create(cls, official_journal, issn_scielo, short_title, user):
        scielo_journals = cls.objects.filter(official=official_journal)
        try:
            scielo_journal = scielo_journals[0]
        except IndexError:
            scielo_journal = cls()
            scielo_journal.official = official_journal
            scielo_journal.issn_scielo = issn_scielo
            scielo_journal.short_title = short_title
            scielo_journal.creator = user
            scielo_journal.save()
        return scielo_journal

    def __unicode__(self):
        return u'%s' % self.official or ''

    def __str__(self):
        return u'%s' % self.official or ''

    base_form_class = CoreAdminModelForm


class Mission(Orderable, RichTextWithLang, CommonControlField):
    journal = ParentalKey(ScieloJournal, on_delete=models.CASCADE, related_name='mission')

    @property
    def data(self):
        d = {}

        if self.journal:
            d.update(self.journal.data)

        return d

    @classmethod
    def get_or_create(cls, scielo_journal, scielo_issn, mission_text, language, user):
        scielo_missions = cls.objects.filter(journal__official__issnl=scielo_issn, language=language)
        try:
            scielo_mission = scielo_missions[0]
        except IndexError:
            scielo_mission = cls()
            scielo_mission.text = mission_text
            scielo_mission.language = language
            scielo_mission.journal = scielo_journal
            scielo_mission.creator = user
            scielo_mission.save()

        return scielo_mission


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
