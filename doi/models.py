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


