from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.edit_handlers import FieldPanel

from core.models import CommonControlField, TextWithLang
from . import choices
from core.forms import CoreAdminModelForm


class CollectionName(TextWithLang):
    @property
    def data(self):
        d = {
            "collection_name__text": self.text,
            "collection_name__language": self.language,
        }

        return d

    def __unicode__(self):
        return u'%s (%s)' % (self.text, self.language)

    def __str__(self):
        return u'%s (%s)' % (self.text, self.language)


class Collection(CommonControlField):
    acron3 = models.CharField(_("Acronym with 3 chars"), max_length=10, null=True, blank=True)
    acron2 = models.CharField(_("Acronym with 2 chars"), max_length=10, null=True, blank=True)
    code = models.CharField(_("Code"), max_length=10, null=True, blank=True)
    domain = models.URLField(_("Domain"), null=True, blank=True)
    name = models.ManyToManyField(CollectionName, verbose_name="Collection Name", max_length=255, blank=True)
    main_name = models.CharField(_("Main name"), max_length=255, null=True, blank=True)
    status = models.CharField(_("Status"), max_length=255, choices=choices.STATUS,
                              null=True, blank=True)
    has_analytics = models.BooleanField(_("Has analytics"), null=True, blank=True)
    type = models.CharField(_("Type"), max_length=255, choices=choices.TYPE,
                            null=True, blank=True)
    is_active = models.BooleanField(_("Is active"), null=True, blank=True)
    foundation_date = models.DateField(_("Foundation data"), null=True, blank=True)

    panels = [
        FieldPanel('acron3'),
        FieldPanel('acron2'),
        FieldPanel('code'),
        FieldPanel('domain'),
        FieldPanel('name'),
        FieldPanel('main_name'),
        FieldPanel('status'),
        FieldPanel('has_analytics'),
        FieldPanel('type'),
        FieldPanel('is_active'),
        FieldPanel('foundation_date'),
    ]

    class Meta:
        verbose_name = _("Collection")
        verbose_name_plural = _("Collections")
        indexes = [
            models.Index(fields=['acron3', ]),
            models.Index(fields=['acron2', ]),
            models.Index(fields=['code', ]),
            models.Index(fields=['domain', ]),
            models.Index(fields=['main_name', ]),
            models.Index(fields=['status', ]),
            models.Index(fields=['type', ]),
        ]

    @property
    def data(self):
        d = {
            "collection__acron3": self.acron3,
            "collection__acron2": self.acron2,
            "collection__code": self.code,
            "collection__domain": self.domain,
            "collection__main_name": self.main_name,
            "collection__status": self.status,
            "collection__has_analytics": self.has_analytics,
            "collection__type": self.type,
            "collection__is_active": self.is_active,
            "collection__is_foundation_date": self.foundation_date,
        }

        if self.name:
            d.update(self.name.data)

        return d

    def __unicode__(self):
        return u'%s' % self.main_name or ''

    def __str__(self):
        return u'%s' % self.main_name or ''

    base_form_class = CoreAdminModelForm
