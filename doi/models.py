from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.edit_handlers import FieldPanel

from core.models import CommonControlField, RichTextWithLang
from core.forms import CoreAdminModelForm
from core.choices import LANGUAGE

from .choices import STATUS


class DOI(CommonControlField):
    value = models.CharField(_('Value'), max_length=100, null=True, blank=True)
    lang = models.CharField(_('Language'), max_length=2, choices=LANGUAGE, null=True, blank=True)

    panels = [
        FieldPanel('value'),
        FieldPanel('lang'),
    ]

    class Meta:
        indexes = [
            models.Index(fields=['value', ]),
            models.Index(fields=['lang', ]),
        ]

    @property
    def data(self):
        return {
            'doi__value': self.value,
            'doi__lang': self.lang,
        }

    def __unicode__(self):
        return u'%s - %s' % (self.value, self.lang) or ''

    def __str__(self):
        return u'%s - %s' % (self.value, self.lang) or ''

    base_form_class = CoreAdminModelForm


class DOIRegistration(CommonControlField):
    doi = models.ManyToManyField(DOI, verbose_name="DOI", blank=True)
    submission_date = models.DateField(_("Submission Date"), max_length=20, null=True, blank=True)
    status = models.CharField(_("Status"), choices=STATUS, max_length=15, null=True, blank=True)

    panels = [
        FieldPanel('doi'),
        FieldPanel('submission_date'),
        FieldPanel('status'),
    ]

    class Meta:
        indexes = [
            models.Index(fields=['submission_date', ]),
            models.Index(fields=['status', ]),
        ]

    @property
    def data(self):
        return {
            'doi_registration__doi': self.doi,
            'doi_registration__submission_date': self.submission_date,
            'doi_registration__status': self.status,
        }

    def __unicode__(self):
        return u'%s - %s - %s' % (self.doi, self.submission_date, self.status) or ''

    def __str__(self):
        return u'%s - %s - %s' % (self.doi, self.submission_date, self.status) or ''

    base_form_class = CoreAdminModelForm
