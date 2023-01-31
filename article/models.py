from django.db import models
from django.utils.translation import gettext as _

from wagtail.admin.edit_handlers import FieldPanel
from wagtail.core.fields import RichTextField

from core.models import CommonControlField, RichTextWithLang, Date
from core.forms import CoreAdminModelForm
from core.choices import LANGUAGE

from institution.models import Sponsor


class Article(CommonControlField):
    pid_v2 = models.CharField(_("PID V2"), blank=True, null=True, max_length=23)
    fundings = models.ManyToManyField("ArticleFunding", verbose_name=_("Fundings"), blank=True)

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
            'article__fundings': [f.data for f in self.fundings.iterator()],
        }

        return _data

    @classmethod
    def get_or_create(cls, pid_v2, fundings, user):
        try:
            return cls.objects.get(pid_v2=pid_v2)
        except cls.DoesNotExist:
            article = cls()
            article.pid_v2 = pid_v2
            article.creator = user
            article.save()
            for funding in fundings:
                article.fundings.add(funding)
            article.save()

            return article

    base_form_class = CoreAdminModelForm


class ArticleFunding(CommonControlField):
    award_id = models.CharField(_("Award ID"), blank=True, null=True, max_length=50)
    funding_source = models.ForeignKey(Sponsor, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        indexes = [
            models.Index(fields=['award_id', ]),
            models.Index(fields=['funding_source', ]),
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
    def get_or_create(cls, award_id, funding_source, user):
        try:
            return cls.objects.get(award_id=award_id, funding_source=funding_source)
        except cls.DoesNotExist:
            article_funding = cls()
            article_funding.award_id = award_id
            article_funding.funding_source = funding_source
            article_funding.creator = user
            article_funding.save()

            return article_funding

    base_form_class = CoreAdminModelForm


class TocSection(RichTextWithLang, CommonControlField):
    text = RichTextField(null=True, blank=True, max_length=100)


