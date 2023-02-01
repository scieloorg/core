from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel

from core.models import CommonControlField, TextWithLang
from core.forms import CoreAdminModelForm


class Vocabulary(CommonControlField):
    name = models.CharField(_('Vocabulary name'), max_length=100, null=True, blank=True)
    acronym = models.CharField(_('Vocabulary acronym'), max_length=10, null=True, blank=True)

    def __unicode__(self):
        return u'%s - %s' % (self.name, self.acronym) or ''

    def __str__(self):
        return u'%s - %s' % (self.name, self.acronym) or ''

    class Meta:
        indexes = [
            models.Index(fields=['name', ]),
            models.Index(fields=['acronym', ]),
        ]

    panels = [
        FieldPanel('name'),
        FieldPanel('acronym'),
    ]

    @property
    def data(self):
        d = {
            "vocabulary__name": self.name,
            "vocabulary__acronym": self.acronym,
        }
        return d

    @classmethod
    def get_or_create(cls, name, acronym, user):
        try:
            return cls.objects.get(name=name)
        except cls.DoesNotExist:
            vocabulary = cls()
            vocabulary.name = name
            vocabulary.acronym = acronym
            vocabulary.creator = user
            vocabulary.save()

    base_form_class = CoreAdminModelForm


