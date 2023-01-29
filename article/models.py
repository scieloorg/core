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


class ArticleFunding(CommonControlField):
    award_id = models.CharField(_("Award ID"), blank=True, null=True, max_length=50)
    funding_source = models.ForeignKey(Sponsor, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=['award_id', ]),
        ]

    panels = [
        FieldPanel('award_id'),
        FieldPanel('funding_source'),
    ]

    def __unicode__(self):
        return u'%s | %s' % (self.award_id, self.funding_source)

    def __str__(self):
        return u'%s | %s' % (self.award_id, self.funding_source)

    @property
    def data(self):
        _data = {
            'article_funding__award_id': self.award_id,
        }
        if self.funding_source:
            _data.update(self.funding_source.data)

        return _data

    @classmethod
    def get_or_create(cls, award_id, funding_source):
        try:
            return cls.objects.filter(award_id=award_id, funding_source=funding_source)
        except:
            article_funding = cls()
            article_funding.award_id = award_id
            article_funding.funding_source = funding_source
            article_funding.save()

            return article_funding

    base_form_class = CoreAdminModelForm
