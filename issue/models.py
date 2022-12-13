from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.edit_handlers import FieldPanel

from core.models import CommonControlField, RichTextWithLang

from core.forms import CoreAdminModelForm

from journal.models import ScieloJournal


class Issue(CommonControlField):
    """
    Class that represent an Issue
    """

    journal = models.ForeignKey(ScieloJournal, verbose_name=_('Journal'), null=True, blank=True,
                                on_delete=models.SET_NULL)
    number = models.CharField(_('Issue number'), max_length=20, null=True, blank=True)
    volume = models.CharField(_('Issue volume'), max_length=20, null=True, blank=True)
    year = models.IntegerField(_('Issue year'), null=True, blank=True)
    month = models.IntegerField(_('Issue month'), null=True, blank=True)

    panels = [
        FieldPanel('journal'),
        FieldPanel('number'),
        FieldPanel('volume'),
        FieldPanel('year'),
        FieldPanel('month'),
    ]

    class Meta:
        verbose_name = _('Issue')
        verbose_name_plural = _('Issues')
        indexes = [
            models.Index(fields=['number', ]),
            models.Index(fields=['volume', ]),
            models.Index(fields=['year', ]),
            models.Index(fields=['month', ]),
        ]

    @property
    def data(self):
        d = dict
        if self.journal:
            d.update(self.journal.data)
        d.update({
            "issue__number": self.number,
            "issue__volume": self.volume,
            "issue__year": self.year,
            "issue__month": self.month,
        })
        return d

    def __unicode__(self):
        return u'%s - %s' % (self.journal, self.number) or ''

    def __str__(self):
        return u'%s - %s' % (self.journal, self.number) or ''

    base_form_class = CoreAdminModelForm
