from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel

from core.models import CommonControlField
from institution.models import Sponsor

from core.forms import CoreAdminModelForm


class Article(CommonControlField):
    pid_v2 = models.CharField(_("PID V2"), blank=True, null=True, max_length=23)
    funding = models.ManyToManyField("ArticleFunding", verbose_name=_("Funding"), blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['pid_v2', ]),
        ]

    def __unicode__(self):
        return u'%s' % self.pid_v2

    def __str__(self):
        return u'%s' % self.pid_v2

    @property
    def data(self):
        _data = {
            'article__pid_v2': self.pid_v2,
            'article__funding': [f.data for f in self.funding.iterator()],
        }

        return _data

    @classmethod
    def get_or_create(cls, pid_v2, funding):
        try:
            return cls.objects.filter(pid_v2=pid_v2, funding=funding)
        except:
            article = cls()
            article.pid_v2 = pid_v2
            article.funding = funding
            article.save()

            return article

    base_form_class = CoreAdminModelForm


