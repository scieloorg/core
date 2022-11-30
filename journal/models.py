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


class Journal(CommonControlField):
class JournalMission(ClusterableModel):
    official_journal = models.ForeignKey('OfficialJournal', null=True, blank=True,
                                         related_name='JournalMission_OfficialJournal',
                                         on_delete=models.SET_NULL)

    panels = [
        FieldPanel('official_journal'),
        InlinePanel('mission', label=_('Mission'), classname="collapsed")
    ]


class FieldMission(Orderable, RichTextWithLang):
    page = ParentalKey(JournalMission, on_delete=models.CASCADE, related_name='mission')

    def __unicode__(self):
        return u'%s %s' % (self.text, self.language)

    def __str__(self):
        return u'%s %s' % (self.text, self.language)


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

    panels = [
        FieldPanel('official'),
    ]

    class Meta:
        verbose_name = _('Journal')
        verbose_name_plural = _('Journals')
        indexes = [
            models.Index(fields=['official', ]),
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
