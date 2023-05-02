from django.db import models
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField

from core.forms import CoreAdminModelForm
from core.models import (
    CommonControlField,
    FlexibleDate,
    Language,
    License,
    RichTextWithLang,
)
from institution.models import Sponsor
from researcher.models import Researcher
from vocabulary.models import Keyword
from journal.models import ScieloJournal
from doi.models import DOI, DOIRegistration


class Article(CommonControlField):
    pid_v2 = models.CharField(_("PID V2"), max_length=23, null=True, blank=True)
    pid_v3 = models.CharField(_("PID V3"), max_length=23, null=True, blank=True)
    journal = models.ForeignKey(
        ScieloJournal,
        verbose_name=_("Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )        
    doi = models.ManyToManyField(DOI, blank=True)
    pub_date_pub = models.CharField(
        _("pub date"),
        max_length=10,
        null=True,
        blank=True,
        help_text="Data de publicação no site."
    )
    pub_date_pub_year = models.CharField(
        max_length=4,
        null=True,
        blank=True,
        help_text="Ano de publicação no site."
    )
    pub_date_collection = models.CharField(
        _("collection pub date"),
        max_length=10,
        null=True,
        blank=True,
        help_text="Data do fascículo."
    )
    pub_date_collection_year = models.CharField(
        max_length=4,
        null=True,
        blank=True,
        help_text="Ano do fascículo"
    )
    pub_date_collection_season = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Ex: Jan-Abr"
    )
    fundings = models.ManyToManyField(
        "ArticleFunding",
        verbose_name=_("Fundings"),
        blank=True
    )
    languages = models.ManyToManyField(Language, blank=True)
    titles = models.ManyToManyField("DocumentTitle", blank=True)
    researchers = models.ManyToManyField(Researcher, blank=True)
    article_type = models.ForeignKey(
        "ArticleType", on_delete=models.SET_NULL, null=True, blank=True
    )
    abstracts = models.ManyToManyField(
        "DocumentAbstract",
        blank=True
    )
    toc_sections = models.ManyToManyField("TocSection", blank=True)
    license = models.ManyToManyField(License, blank=True)
    volume = models.CharField(max_length=64, null=True, blank=True)
    issue = models.CharField(max_length=64, null=True, blank=True)
    first_page = models.CharField(max_length=5, null=True, blank=True)
    last_page = models.CharField(max_length=5, null=True, blank=True)
    elocation_id = models.CharField(max_length=20, null=True, blank=True)
    keywords = models.ManyToManyField(Keyword, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "pid_v2",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s" % self.pid_v2

    def __str__(self):
        return "%s" % self.pid_v2

    @property
    def data(self):
        _data = {
            "article__pid_v2": self.pid_v2,
            "article__fundings": [f.data for f in self.fundings.iterator()],
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
    funding_source = models.ForeignKey(
        Sponsor, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "award_id",
                ]
            ),
            models.Index(
                fields=[
                    "funding_source",
                ]
            ),
        ]

    panels = [
        FieldPanel("award_id"),
        FieldPanel("funding_source"),
    ]

    def __unicode__(self):
        return "%s | %s" % (self.award_id, self.funding_source)

    def __str__(self):
        return "%s | %s" % (self.award_id, self.funding_source)

    @property
    def data(self):
        _data = {
            "article_funding__award_id": self.award_id,
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


class DocumentTitle(RichTextWithLang, CommonControlField):
    ...


class ArticleType(models.Model):
    text = models.TextField(_("Text"), null=True, blank=True)


class DocumentAbstract(RichTextWithLang, CommonControlField):
    ...


class ArticleEventType(CommonControlField):
    code = models.CharField(_("Code"), blank=True, null=True, max_length=20)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "code",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s" % self.code

    def __str__(self):
        return "%s" % self.code

    @property
    def data(self):
        return dict(article_event_type__code=self.code)

    @classmethod
    def get_or_create(cls, code, user):
        try:
            return cls.objects.get(code=code)
        except cls.DoesNotExist:
            article_event_type = cls()
            article_event_type.code = code
            article_event_type.creator = user
            article_event_type.save()

            return article_event_type


class ArticleHistory(CommonControlField):
    event_type = models.ForeignKey(
        ArticleEventType, null=True, blank=True, on_delete=models.SET_NULL
    )
    date = models.ForeignKey(
        FlexibleDate, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "event_type",
                ]
            ),
            models.Index(
                fields=[
                    "date",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s (%s)" % (self.code, self.date)

    def __str__(self):
        return "%s (%s)" % (self.code, self.date)

    @property
    def data(self):
        return dict(
            article_history__event_type=self.event_type,
            article_history__date=self.date.data,
        )


class ArticleCountType(CommonControlField):
    code = models.CharField(_("Code"), blank=True, null=True, max_length=20)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "code",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s" % self.code

    def __str__(self):
        return "%s" % self.code

    @property
    def data(self):
        return dict(article_count_type__code=self.code)

    @classmethod
    def get_or_create(cls, code, user):
        try:
            return cls.objects.get(code=code)
        except cls.DoesNotExist:
            article_count_type = cls()
            article_count_type.code = code
            article_count_type.creator = user
            article_count_type.save()

            return article_count_type


class ArticleCount(CommonControlField):
    count_type = models.ForeignKey(
        ArticleCountType, null=True, blank=True, on_delete=models.SET_NULL
    )
    count = models.IntegerField(_("Count"), null=True, blank=True)
    language = models.ForeignKey(
        Language,
        on_delete=models.SET_NULL,
        verbose_name=_("Language"),
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "count_type",
                ]
            ),
            models.Index(
                fields=[
                    "language",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s | %s | %s" % (self.count_type, self.count, self.language)

    def __str__(self):
        return "%s | %s | %s" % (self.count_type, self.count, self.language)

    @property
    def data(self):
        return dict(
            article_count__count_type=self.count_type,
            article_count__count=self.count,
            article_count__language=self.language,
        )


class TocSection(RichTextWithLang, CommonControlField):
    """
    <article-categories>
        <subj-group subj-group-type="heading">
          <subject>NOMINATA</subject>
        </subj-group>
      </article-categories>
    """
    text = RichTextField(
        max_length=100,
        blank=True,
        null=True,
        help_text="For JATs is subject."
    )

    class Meta:
        verbose_name = _("TocSection")
        verbose_name_plural = _("TocSections")

    def __unicode__(self):
        return f"{self.text}"

    def __str__(self):
        return f"{self.text}"


class SubArticle(models.Model):
    titles = models.ManyToManyField("DocumentTitle", blank=True)
    # lang = models.CharField(max_length=2, null=True, blank=True)
    article = models.ForeignKey(
        Article, on_delete=models.SET_NULL, null=True, blank=True
    )
    article_type = models.ForeignKey(
        "ArticleType", on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = _("SubArticle")
        verbose_name_plural = _("SubArticles")

    def __str__(self):
        return f"{self.title}"
