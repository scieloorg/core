import os
import sys

from datetime import datetime

from django.core.files.base import ContentFile
from django.db import models, IntegrityError
from django.db.utils import DataError
from django.utils.translation import gettext as _
from packtools.sps.formats import pubmed, pmc, crossref
from packtools.sps.pid_provider.xml_sps_lib import generate_finger_print
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.models import Orderable
from wagtail.admin.panels import FieldPanel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import (
    CommonControlField,
    FlexibleDate,
    Language,
    License,
    LicenseStatement,
    TextLanguageMixin,
)
from doi.models import DOI
from doi_manager.models import CrossRefConfiguration
from institution.models import Institution, Sponsor
from issue.models import Issue, TocSection
from journal.models import Journal, SciELOJournal
from pid_provider.provider import PidProvider
from researcher.models import Researcher, InstitutionalAuthor
from vocabulary.models import Keyword
from tracker.models import UnexpectedEvent


class Article(CommonControlField, ClusterableModel):
    pid_v2 = models.CharField(_("PID V2"), max_length=23, null=True, blank=True)
    pid_v3 = models.CharField(_("PID V3"), max_length=23, null=True, blank=True)
    sps_pkg_name = models.CharField(
        _("Package name"), max_length=64, null=True, blank=True
    )
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
    collab = models.ManyToManyField(InstitutionalAuthor, blank=True)
    article_type = models.CharField(max_length=50, null=True, blank=True)
    # abstracts = models.ManyToManyField("DocumentAbstract", blank=True)
    toc_sections = models.ManyToManyField(TocSection, blank=True)
    license_statements = models.ManyToManyField(LicenseStatement, blank=True)
    license = models.ForeignKey(
        License, on_delete=models.SET_NULL, null=True, blank=True
    )
    issue = models.ForeignKey(Issue, on_delete=models.SET_NULL, null=True, blank=True)
    first_page = models.CharField(max_length=20, null=True, blank=True)
    last_page = models.CharField(max_length=20, null=True, blank=True)
    elocation_id = models.CharField(max_length=64, null=True, blank=True)
    keywords = models.ManyToManyField(Keyword, blank=True)
    publisher = models.ForeignKey(
        Institution,
        verbose_name=_("Publisher"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    valid = models.BooleanField(default=False, blank=True, null=True)

    panels_ids = [
        FieldPanel("pid_v2"),
        FieldPanel("pid_v3"),
        AutocompletePanel("doi"),
        AutocompletePanel("journal"),
        AutocompletePanel("issue"),
        FieldPanel("pub_date_day"),
        FieldPanel("pub_date_month"),
        FieldPanel("pub_date_year"),
        FieldPanel("first_page"),
        FieldPanel("last_page"),
        FieldPanel("elocation_id"),
    ]
    panels_languages = [
        FieldPanel("article_type"),
        AutocompletePanel("toc_sections"),
        AutocompletePanel("languages"),
        AutocompletePanel("titles"),
        InlinePanel("abstracts", label=_("Abstract")),
        AutocompletePanel("keywords"),
        AutocompletePanel("license"),
    ]
    panels_researchers = [
        AutocompletePanel("researchers"),
        AutocompletePanel("collab"),
    ]
    panels_institutions = [
        AutocompletePanel("publisher"),
        AutocompletePanel("fundings"),
    ]

    panels_formats = [
        AutocompletePanel("publisher"),
        AutocompletePanel("fundings"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_ids, heading=_("Identification")),
            ObjectList(panels_languages, heading=_("Data with language")),
            ObjectList(panels_researchers, heading=_("Researchers")),
            ObjectList(panels_institutions, heading=_("Publisher and Sponsors")),
        ]
    )

    class Meta:
        ordering = ["-updated", "-created", "sps_pkg_name"]
        indexes = [
            models.Index(
                fields=[
                    "pid_v2",
                ]
            ),
            models.Index(
                fields=[
                    "sps_pkg_name",
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
        return self.sps_pkg_name or self.pid_v3 or f"{self.doi.first()}" or self.title

    def __str__(self):
        return self.sps_pkg_name or self.pid_v3 or f"{self.doi.first()}" or self.title

    @property
    def xmltree(self):
        return PidProvider.get_xmltree(self.pid_v3)

    @property
    def abstracts(self):
        return DocumentAbstract.objects.filter(article=self)

    @property
    def collections(self):
        scielo_journals = SciELOJournal.objects.filter(journal=self.journal)
        for scielo_journal in scielo_journals:
            yield scielo_journal.collection

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

    def is_indexed_at(self, db_acronym):
        return bool(self.journal) and self.journal.is_indexed_at(db_acronym)

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
    award_id = models.CharField(_("Award ID"), blank=True, null=True, max_length=100)
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
            try:
                article_funding = cls()
                article_funding.award_id = award_id
                article_funding.funding_source = funding_source
                article_funding.creator = user
                article_funding.save()
                return article_funding
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail=dict(
                        function="article.models.ArticleFunding.get_or_create",
                        award_id=award_id,
                    ),
                )

    base_form_class = CoreAdminModelForm


class DocumentTitle(TextLanguageMixin, CommonControlField):
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
            try:
                return cls.objects.get(plain_text=title)
            except cls.MultipleObjectsReturned:
                return cls.objects.first(plain_text=title)
        raise ValueError("DocumentTitle requires title parameter")

    @classmethod
    def create_or_update(cls, title, rich_text, language, user):
        try:
            obj = cls.get(title=title)
            obj.updated_by = user
        except cls.DoesNotExist:
            obj = cls()
            obj.plain_text = title
            obj.creator = user

        obj.language = language or obj.language
        obj.rich_text = rich_text or obj.rich_text
        obj.save()
        return obj


class ArticleType(models.Model):
    text = models.TextField(_("Text"), null=True, blank=True)

    def __str__(self):
        return self.text


class DocumentAbstract(TextLanguageMixin, CommonControlField, Orderable):
    article = ParentalKey(
        Article,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="abstracts",
    )

    panels = [
        AutocompletePanel("language"),
        FieldPanel("plain_text"),
    ]
    base_form_class = CoreAdminModelForm

    class Meta:
        unique_together = [
            ("article", "language"),
        ]
        indexes = [
            models.Index(
                fields=[
                    "language",
                ]
            ),
        ]

    def __str__(self):
        return f"[{self.language}] {self.plain_text}"

    @classmethod
    def get(
        cls,
        article,
        language,
    ):
        if article:
            try:
                return cls.objects.get(article=article, language=language)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(article=article, language=language).first()
        raise ValueError("DocumentAbstract.get requires article parameter")

    @classmethod
    def create(
        cls,
        user,
        article,
        language,
        text,
    ):
        try:
            obj = cls()
            obj.creator = user
            obj.plain_text = text or obj.plain_text
            obj.article = article or obj.article
            obj.language = language or obj.language
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(article=article, language=language)

    @classmethod
    def create_or_update(
        cls,
        user,
        article,
        language,
        text,
        rich_text,
    ):
        try:
            obj = cls.get(article=article, language=language)
            obj.plain_text = text or obj.plain_text
            obj.article = article or obj.article
            obj.rich_text = rich_text or obj.rich_text
            obj.language = language or obj.language
            obj.updated_by = user
            obj.save()
            return obj
        except cls.DoesNotExist:
            return cls.create(user, article, language, text)


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

    panels = [AutocompletePanel("count_type"), AutocompletePanel("language")]

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


def article_directory_path(instance, filename):
    try:
        return os.path.join(
            *instance.article.sps_pkg_name.split("-"), instance.format_name, filename
        )
    except AttributeError:
        return os.path.join(instance.article.pid_v3, instance.format_name, filename)


class ArticleFormat(CommonControlField):

    article = ParentalKey(
        Article,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="format",
    )
    format_name = models.CharField(
        _("Article Format"), max_length=20, null=True, blank=True
    )
    version = models.PositiveIntegerField(null=True, blank=True)
    file = models.FileField(
        null=True,
        blank=True,
        verbose_name=_("File"),
        upload_to=article_directory_path,
    )
    report = models.JSONField(null=True, blank=True)
    valid = models.BooleanField(default=None, null=True, blank=True)
    finger_print = models.CharField(max_length=64, null=True, blank=True)

    base_form_class = CoreAdminModelForm
    panels = [
        FieldPanel("file"),
        FieldPanel("format_name"),
        FieldPanel("version"),
        FieldPanel("report"),
    ]

    class Meta:
        verbose_name = _("Article Format")
        verbose_name_plural = _("Article Formats")
        unique_together = [("article", "format_name", "version")]
        indexes = [
            models.Index(
                fields=[
                    "article",
                ]
            ),
            models.Index(
                fields=[
                    "format_name",
                ]
            ),
            models.Index(
                fields=[
                    "version",
                ]
            ),
        ]

    def __unicode__(self):
        return f"{self.article} {self.format_name} {self.created.isoformat()}"

    def __str__(self):
        return f"{self.article} {self.format_name} {self.created.isoformat()}"

    @classmethod
    def get(cls, article, format_name=None, version=None):
        if article and format_name and version:
            try:
                return cls.objects.get(
                    article=article, format_name=format_name, version=version
                )
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(
                    article=article, format_name=format_name, version=version
                ).last()
        raise ValueError(
            "ArticleFormat.get requires article and format_name and version"
        )

    @classmethod
    def create(cls, user, article, format_name=None, version=None):
        if article or format_name or version:
            try:
                obj = cls()
                obj.article = article
                obj.format_name = format_name
                obj.version = version
                obj.creator = user
                obj.save()
                return obj
            except IntegrityError:
                return cls.get(article, format_name, version)
        raise ValueError(
            "ArticleFormat.create requires article and format_name and version"
        )

    @classmethod
    def create_or_update(cls, user, article, format_name=None, version=None):
        try:
            obj = cls.get(article, format_name=format_name, version=version)
            obj.updated_by = user
            obj.format_name = format_name or obj.format_name
            obj.version = version or obj.version
            obj.save()
        except cls.DoesNotExist:
            obj = cls.create(user, article, format_name, version)
        return obj

    def save_file(self, filename, content):
        finger_print = generate_finger_print(content)
        if finger_print != self.finger_print:
            try:
                self.file.delete()
            except Exception as e:
                pass
            self.file.save(filename, ContentFile(content))
            self.finger_print = finger_print
            self.save()

    @classmethod
    def generate(
        cls,
        user,
        article,
        format_name,
        filename,
        function_generate_format,
        indexed_check=False,
        data=None,
        version=None,
    ):
        if indexed_check and not article.is_indexed_at(format_name):
            return
        try:
            version = version or 1
            obj = None
            obj = cls.create_or_update(user, article, format_name, version)
            xmltree = article.xmltree
            if data is not None:
                content = function_generate_format(xmltree, data=data)
            else:
                content = function_generate_format(xmltree)
            obj.save_file(filename, content)
            obj.report = None
            obj.save()
            return obj
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            unexpected_event = UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    function="article.models.ArticleFormat.generate",
                    format_name=format_name,
                    article_pid_v3=article.pid_v3,
                    sps_pkg_name=article.sps_pkg_name,
                ),
            )
            if obj:
                obj.report = unexpected_event.data
                obj.valid = False
                obj.save()

    @classmethod
    def generate_formats(cls, user, article):
        for doi in article.doi.all():
            if not doi.value:
                break
            try:
                prefix = doi.value.split("/")[0]
                crossref_data = CrossRefConfiguration.get_data(prefix)
                cls.generate(
                    user,
                    article,
                    "crossref",
                    article.sps_pkg_name + ".xml",
                    crossref.pipeline_crossref,
                    data=crossref_data,
                )
            except CrossRefConfiguration.DoesNotExist:
                break
        cls.generate(
            user,
            article,
            "pubmed",
            article.sps_pkg_name + ".xml",
            pubmed.pipeline_pubmed,
            indexed_check=False,
        )
        cls.generate(
            user,
            article,
            "pmc",
            article.sps_pkg_name + ".xml",
            pmc.pipeline_pmc,
            indexed_check=False,
        )
