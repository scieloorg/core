from datetime import datetime

from django.db import models
from django.db.models import Case, When
from django.utils.translation import gettext as _
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import (
    CommonControlField,
    FlexibleDate,
    Language,
    License,
    RichTextWithLang,
)
from doi.models import DOI
from institution.models import Institution, Sponsor
from issue.models import Issue, TocSection
from journal.models import Journal
from researcher.models import Researcher
from vocabulary.models import Keyword


class Article(CommonControlField):
    pid_v2 = models.CharField(_("PID V2"), max_length=23, null=True, blank=True)
    pid_v3 = models.CharField(_("PID V3"), max_length=23, null=True, blank=True)
    journal = models.ForeignKey(
        Journal,
        verbose_name=_("Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    doi = models.ManyToManyField(DOI, blank=True)
    pub_date_day = models.CharField(
        _("pub date day"),
        max_length=10,
        null=True,
        blank=True,
        help_text="Dia de publicação no site.",
    )
    pub_date_month = models.CharField(
        _("pub date month"),
        max_length=10,
        null=True,
        blank=True,
        help_text="Mês de publicação no site.",
    )
    pub_date_year = models.CharField(
        max_length=4, null=True, blank=True, help_text="Ano de publicação no site."
    )
    fundings = models.ManyToManyField(
        "ArticleFunding", verbose_name=_("Fundings"), blank=True
    )
    languages = models.ManyToManyField(Language, blank=True)
    titles = models.ManyToManyField("DocumentTitle", blank=True)
    researchers = models.ManyToManyField(Researcher, blank=True)
    article_type = models.ForeignKey(
        "ArticleType", on_delete=models.SET_NULL, null=True, blank=True
    )
    abstracts = models.ManyToManyField("DocumentAbstract", blank=True)
    toc_sections = models.ManyToManyField(TocSection, blank=True)
    license = models.ManyToManyField(License, blank=True)
    issue = models.ForeignKey(Issue, on_delete=models.SET_NULL, null=True, blank=True)
    first_page = models.CharField(max_length=10, null=True, blank=True)
    last_page = models.CharField(max_length=10, null=True, blank=True)
    elocation_id = models.CharField(max_length=20, null=True, blank=True)
    keywords = models.ManyToManyField(Keyword, blank=True)
    publisher = models.ForeignKey(
        Institution,
        verbose_name=_("Publisher"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )


    panels = [
        FieldPanel("pid_v2"),
        FieldPanel("pid_v3"),
        AutocompletePanel("journal"),
        AutocompletePanel("doi"),
        FieldPanel("pub_date_day"),
        FieldPanel("pub_date_month"),
        FieldPanel("pub_date_year"),
        AutocompletePanel("fundings"),
        AutocompletePanel("languages"),
        AutocompletePanel("titles"),
        AutocompletePanel("researchers"),
        FieldPanel("article_type"),
        AutocompletePanel("abstracts"),
        AutocompletePanel("toc_sections"),
        AutocompletePanel("license"),
        AutocompletePanel("issue"),
        FieldPanel("first_page"),
        FieldPanel("last_page"),
        FieldPanel("elocation_id"),
        AutocompletePanel("keywords"),
        AutocompletePanel("publisher"),
    ]

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "pid_v2",
                ]
            ),
            models.Index(
                fields=[
                    "pid_v3",
                ]
            ),
            models.Index(
                fields=[
                    "pub_date_year",
                ]
            ),
        ]

    def __unicode__(self):
        return "%s" % self.pid_v2

    def __str__(self):
        return "%s" % self.pid_v2

    @property
    def collection(self):
        return self.journal.collection

    @classmethod
    def last_created_date(cls):
        try:
            last_created = cls.objects.filter(
                pid_v3__isnull=False,
            ).latest("created")
            return last_created.created
        except (AttributeError, cls.DoesNotExist):
            return datetime(1, 1, 1)

    @property
    def data(self):
        _data = {
            "article__pid_v2": self.pid_v2,
            "article__pid_v3": self.pid_v3,
            "article__fundings": [f.data for f in self.fundings.iterator()],
        }

        return _data

    @classmethod
    def get_or_create(cls, doi, pid_v2, fundings, user):
        try:
            return cls.objects.get(doi__in=doi, pid_v2=pid_v2)
        except cls.DoesNotExist:
            article = cls()
            article.pid_v2 = pid_v2
            article.creator = user
            article.save()
            article.doi.set(doi)
            if fundings:
                for funding in fundings:
                    article.fundings.add(funding)
            return article

    def set_date_pub(self, dates):
        if dates:
            self.pub_date_day = dates.get("day")
            self.pub_date_month = dates.get("month")
            self.pub_date_year = dates.get("year")
            self.save()

    def set_pids(self, pids):
        self.pid_v2 = pids.get("v2")
        self.pid_v3 = pids.get("v3")
        self.save()

    # @property
    # def get_abstracts_order_by_lang_pt(self):
    #     return self.abstracts.all().order_by(
    #             Case(
    #                 When(language__code2='pt', then=0),
    #                 default=1,
    #                 output_field=models.IntegerField()
    #             )
    #         )

    base_form_class = CoreAdminModelForm


class ArticleFunding(CommonControlField):
    award_id = models.CharField(_("Award ID"), blank=True, null=True, max_length=50)
    funding_source = models.ForeignKey(
        Sponsor, null=True, blank=True, on_delete=models.SET_NULL
    )
    
    autocomplete_search_field = "award_id"
    
    def autocomplete_label(self):
        return str(self)
        
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
        AutocompletePanel("funding_source"),
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
            if funding_source:
                article_funding.funding_source = Sponsor.get_or_create(
                    inst_name=funding_source,
                    user=user,
                    inst_acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    location=None,
                    official=None,
                    is_official=None,
                )
            article_funding.creator = user
            article_funding.save()

            return article_funding

    base_form_class = CoreAdminModelForm


class DocumentTitle(RichTextWithLang, CommonControlField):
    ...
    
    autocomplete_search_field = "plain_text"

    def autocomplete_label(self):
        return str(self)
    
    def __str__(self):
        return f"{self.plain_text} - {self.language}"
    
    @classmethod
    def get(
        cls,
        title,
    ):
        if title:
            return cls.objects.get(plain_text=title)
        raise ValueError("DocumentTitle requires title paramenter")
    
    @classmethod
    def create_or_update(cls, title, title_rich, language, user):
        try:
            obj = cls.get(title=title)
        except cls.DoesNotExist:
            obj = cls()
            obj.plain_text = title
            obj.creator = user
            
        obj.language = language
        obj.rich_text = title_rich
        obj.updated_by = user
        obj.save()
        return obj


class ArticleType(models.Model):
    text = models.TextField(_("Text"), null=True, blank=True)

    def __str__(self):
        return self.text


class DocumentAbstract(RichTextWithLang, CommonControlField):
    ...

    autocomplete_search_field = "plain_text"

    def autocomplete_label(self):
        return str(self)

    def __str__(self):
        return f"{self.plain_text} - {self.language}"
    

    @classmethod
    def get(
        cls,
        text,
    ):
        if text:
            return cls.objects.get(plain_text=text)
        raise ValueError("DocumentAbstract.get requires text paramenter")

    @classmethod
    def create_or_update(
        cls,
        text,
        language,
        user,
    ):
        try:
            obj = cls.get(text=text)
        except cls.DoesNotExist:
            obj = cls()
            obj.plain_text = text
            obj.creator = user

        obj.language = language
        obj.updated_by = user
        obj.save()
        return obj


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

    panels = [
        AutocompletePanel("event_type"),
        AutocompletePanel("date"),
    ]

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

    panels = [
        AutocompletePanel("count_type"),
        AutocompletePanel("language")
    ]

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


class SubArticle(models.Model):
    titles = models.ManyToManyField("DocumentTitle", blank=True)
    # lang = models.CharField(max_length=2, null=True, blank=True)
    article = models.ForeignKey(
        Article, on_delete=models.SET_NULL, null=True, blank=True
    )
    article_type = models.ForeignKey(
        "ArticleType", on_delete=models.SET_NULL, null=True, blank=True
    )

    panels = [
        AutocompletePanel("titles"),
        AutocompletePanel("article"),
        AutocompletePanel("article_type"),
    ]

    class Meta:
        verbose_name = _("SubArticle")
        verbose_name_plural = _("SubArticles")

    def __str__(self):
        return f"{self.title}"
