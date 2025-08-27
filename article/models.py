import logging
import os
import sys
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import IntegrityError, models
from django.db.models import Q
from django.db.utils import DataError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_lazy as _
from django_prometheus.models import ExportModelOperationsMixin
from legendarium.formatter import descriptive_format
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from packtools.sps.formats import crossref, pmc, pubmed
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre, generate_finger_print
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from article import choices
from core.forms import CoreAdminModelForm
from core.models import CommonControlField  # Ajuste o import conforme sua estrutura
from core.models import (
    FlexibleDate,
    Language,
    License,
    LicenseStatement,
    TextLanguageMixin,
)
from doi.models import DOI
from doi_manager.models import CrossRefConfiguration
from institution.models import Publisher, Sponsor
from issue.models import Issue, TocSection
from journal.models import Journal, SciELOJournal
from pid_provider.choices import PPXML_STATUS_DONE
from pid_provider.models import PidProviderXML
from pid_provider.provider import PidProvider
from researcher.models import InstitutionalAuthor, Researcher
from tracker.models import UnexpectedEvent
from vocabulary.models import Keyword


class Article(
    ExportModelOperationsMixin("article"), CommonControlField, ClusterableModel
):
    pp_xml = models.ForeignKey(
        PidProviderXML,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    data_status = models.CharField(
        _("Data status"),
        max_length=15,
        null=True,
        blank=True,
        choices=choices.DATA_STATUS,
        default=choices.DATA_STATUS_UNDEF,
    )
    pid_v2 = models.CharField(_("PID V2"), max_length=23, null=True, blank=True)
    pid_v3 = models.CharField(
        _("PID V3"), max_length=23, null=True, blank=True, unique=True
    )
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
    valid = models.BooleanField(default=False, blank=True, null=True)
    errors = models.JSONField(default=None, blank=True, null=True)

    panels_ids = [
        FieldPanel("data_status"),
        FieldPanel("valid"),
        FieldPanel("pid_v2", read_only=True),
        FieldPanel("pid_v3", read_only=True),
        AutocompletePanel("doi", read_only=True),
        AutocompletePanel("journal", read_only=True),
        AutocompletePanel("issue", read_only=True),
        FieldPanel("pub_date_day", read_only=True),
        FieldPanel("pub_date_month", read_only=True),
        FieldPanel("pub_date_year", read_only=True),
        FieldPanel("first_page", read_only=True),
        FieldPanel("last_page", read_only=True),
        FieldPanel("elocation_id", read_only=True),
    ]
    panels_languages = [
        FieldPanel("article_type", read_only=True),
        AutocompletePanel("toc_sections", read_only=True),
        AutocompletePanel("languages", read_only=True),
        AutocompletePanel("titles", read_only=True),
        InlinePanel("abstracts", label=_("Abstract")),
        AutocompletePanel("keywords", read_only=True),
        AutocompletePanel("license", read_only=True),
        # AutocompletePanel("license_statements"),
    ]
    panels_researchers = [
        AutocompletePanel("researchers", read_only=True),
        AutocompletePanel("collab", read_only=True),
    ]
    panels_institutions = [
        AutocompletePanel("fundings", read_only=True),
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
                    "id",
                ]
            ),
            models.Index(
                fields=[
                    "valid",
                ]
            ),
            models.Index(
                fields=[
                    "data_status",
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
        if self.journal:
            for item in self.journal.scielojournal_set.all().select_related(
                "collection"
            ):
                yield item.collection
        # scielo_journals = SciELOJournal.objects.select_related("collection").filter(journal=self.journal)
        # for scielo_journal in scielo_journals:
        #     yield scielo_journal.collection

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

    @property
    def source(self):
        """
        Return the format: Acta Cirúrgica Brasileira, Volume: 37, Issue: 7, Article number: e370704, Published: 10 OCT 2022
        """
        leg_dict = {
            "title": self.journal.title if self.journal else "",
            "pubdate": self.issue.year if self.issue else "",
            "volume": self.issue.volume if self.issue else "",
            "number": self.issue.number if self.issue else "",
            "fpage": self.first_page,
            "lpage": self.last_page,
            "elocation": self.elocation_id,
        }

        try:
            return descriptive_format(**leg_dict)
        except Exception as ex:
            logging.exception("Erro on article %s, error: %s" % (self.pid_v2, ex))
            return ""
        
    @property
    def pub_date(self):
        year = self.pub_date_year or ''
        month = self.pub_date_month or ''
        day = self.pub_date_day or ''
        
        if year and month and day:
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        elif year and month:
            return f"{year}-{month.zfill(2)}"
        
        else:
            return year

    @classmethod
    def get(
        cls,
        pid_v3,
    ):
        if pid_v3:
            return cls.objects.get(pid_v3=pid_v3)
        raise ValueError("Article requires pid_v3")

    @classmethod
    def create(
        cls,
        pid_v3,
        user,
    ):
        try:
            obj = cls()
            obj.pid_v3 = pid_v3
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(pid_v3=pid_v3)

    @classmethod
    def get_or_create(
        cls,
        pid_v3,
        user,
    ):
        try:
            return cls.get(pid_v3=pid_v3)
        except cls.DoesNotExist:
            return cls.create(pid_v3=pid_v3, user=user)

    @classmethod
    def mark_as_deleted_articles_without_pp_xml(cls, user):
        """
        Marca artigos como DATA_STATUS_DELETED quando pp_xml é None.

        Args:
            user: Usuário que está executando a operação

        Returns:
            int: Número de artigos atualizados
        """
        try:
            return (
                cls.objects.filter(pp_xml__isnull=True)
                .exclude(data_status=choices.DATA_STATUS_DELETED)
                .update(
                    data_status=choices.DATA_STATUS_DELETED,
                    updated_by=user,
                    updated=datetime.utcnow(),
                )
            )

        except Exception as exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=exception,
                exc_traceback=exc_traceback,
                action="article.models.Article.mark_articles_as_deleted_without_pp_xml",
                detail=None,
            )

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
        if not award_id or not funding_source:
            raise ValueError(
                "ArticleFunding.get_or_create requires award_id and funding_source"
            )
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


def article_source_path(instance, filename):
    """Define o caminho para upload de arquivos de fonte de artigos"""
    subdir = "/".join(instance.sps_pkg_name.split("-"))
    return f"article_sources/{subdir}/{filename}"


class ArticleSource(CommonControlField):
    """
    Represent article sources with URL or file
    Fields:
        created
        updated
        url
        file
        source_date
        status
    """

    class StatusChoices(models.TextChoices):
        PENDING = "pending", _("Pending")
        PROCESSING = "processing", _("Processing")
        COMPLETED = "completed", _("Completed")
        ERROR = "error", _("Error")
        REPROCESS = "reprocess", _("Reprocess")

    url = models.URLField(
        verbose_name=_("Article URL"),
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Article URL"),
    )
    file = models.FileField(
        verbose_name=_("Article file"),
        upload_to=article_source_path,
        null=True,
        blank=True,
        help_text=_("Upload article file"),
    )
    source_date = models.CharField(
        verbose_name=_("Source date"),
        max_length=10,
        null=True,
        blank=True,
        help_text=_("Date of data collection or original data date"),
    )
    status = models.CharField(
        verbose_name=_("Status"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        help_text=_("Processing status of the article source"),
    )
    pid_provider_xml = models.ForeignKey(
        PidProviderXML,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("PID Provider XML"),
        help_text=_("Related PID Provider XML instance"),
    )
    article = models.ForeignKey(
        Article,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Article"),
        help_text=_("Related Article instance"),
    )
    detail = models.JSONField(null=True, blank=True, default=None)

    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("url", read_only=True),
        FieldPanel("file", read_only=True),
        FieldPanel("source_date", read_only=True),
        FieldPanel("status"),
        FieldPanel("pid_provider_xml", read_only=True),
        FieldPanel("article", read_only=True),
        FieldPanel("detail", read_only=True),
    ]

    @staticmethod
    def autocomplete_custom_queryset_filter(search_term):
        return ArticleSource.objects.filter(
            Q(url__icontains=search_term) | Q(file__icontains=search_term)
        )

    def autocomplete_label(self):
        if self.url:
            return f"{self.url}"
        elif self.file:
            return f"{self.file.name}"
        return f"ArticleSource #{self.pk}"

    class Meta:
        verbose_name = _("Article Source")
        verbose_name_plural = _("Article Sources")
        indexes = [
            models.Index(fields=["url"]),
            models.Index(fields=["source_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["status", "updated"]),
            models.Index(fields=["pid_provider_xml"]),
            models.Index(fields=["article"]),
        ]

    def __unicode__(self):
        if self.url:
            return f"{self.url}"
        elif self.file:
            return f"{self.file.name}"
        return f"ArticleSource #{self.pk}"

    def __str__(self):
        if self.url:
            return f"{self.url}"
        elif self.file:
            return f"{self.file.name}"
        return f"ArticleSource #{self.pk}"

    @classmethod
    def get(cls, url):
        if url:
            try:
                return cls.objects.get(url__iexact=url)
            except cls.MultipleObjectsReturned:
                return cls.objects.filter(url__iexact=url).first()

        raise ValueError("ArticleSource.get requires url")

    @classmethod
    def create(cls, user, url=None, source_date=None):
        if not url:
            raise ValueError("ArticleSource.create requires url")

        try:
            obj = cls()
            obj.creator = user
            obj.url = url
            obj.source_date = source_date
            obj.status = cls.StatusChoices.PENDING
            obj.save()
            try:
                obj.create_file()
            except Exception as e:
                pass
            return obj
        except IntegrityError:
            return cls.get(url=url)

    @classmethod
    def create_or_update(cls, user, url=None, source_date=None, force_update=None):
        try:
            logging.info(f"ArticleSource.create_or_update {url}")
            obj = cls.get(url=url)

            if (
                force_update
                or (source_date and source_date != obj.source_date)
                or not obj.file or not obj.file.path or not os.path.isfile(obj.file.path)
            ):
                logging.info(f"updating source: {(source_date, obj.source_date)}")
                logging.info(f"updating file: {not obj.file or not obj.file.path or not os.path.isfile(obj.file.path)}")
                obj.create_file()
                obj.updated_by = user
                obj.source_date = source_date
                obj.status = cls.StatusChoices.REPROCESS
                obj.save()

        except cls.DoesNotExist:
            obj = cls.create(user, url=url, source_date=source_date)
        return obj

    @property
    def sps_pkg_name(self):
        if not hasattr(self, "_sps_pkg_name") or not self._sps_pkg_name:
            try:
                xml_with_pre = list(XMLWithPre.create(path=self.file.path))[0]
            except:
                xml_with_pre = list(XMLWithPre.create(uri=self.url))[0]
            self._sps_pkg_name = xml_with_pre.sps_pkg_name
        return self._sps_pkg_name

    def create_file(self):
        logging.info(f"ArticleSource.create_file for {self.url}")
        xml_with_pre = list(XMLWithPre.create(uri=self.url))[0]
        self.save_file(
            f"{self.sps_pkg_name}.xml", xml_with_pre.tostring(pretty_print=True)
        )

    def save_file(self, filename, content):
        try:
            self.file.delete(save=False)
        except Exception as e:
            logging.exception(e)
        self.file.save(filename, ContentFile(content))

    # Métodos para controle de status
    def mark_as_processing(self):
        """Marca como processando"""
        self.status = self.StatusChoices.PROCESSING
        self.save()

    def mark_as_completed(self):
        """Marca como concluído"""
        self.status = self.StatusChoices.COMPLETED
        self.save()

    def mark_as_error(self):
        """Marca como erro"""
        self.status = self.StatusChoices.ERROR
        self.save()

    def mark_for_reprocess(self):
        """Marca para reprocessamento"""
        self.status = self.StatusChoices.REPROCESS
        self.save()

    # Métodos de consulta por status
    @classmethod
    def get_pending(cls):
        """Retorna fontes pendentes"""
        return cls.objects.filter(status=cls.StatusChoices.PENDING)

    @classmethod
    def get_for_reprocess(cls):
        """Retorna fontes marcadas para reprocessamento"""
        return cls.objects.filter(status=cls.StatusChoices.REPROCESS)

    @classmethod
    def get_processing(cls):
        """Retorna fontes em processamento"""
        return cls.objects.filter(status=cls.StatusChoices.PROCESSING)

    @classmethod
    def get_completed(cls):
        """Retorna fontes concluídas"""
        return cls.objects.filter(status=cls.StatusChoices.COMPLETED)

    @classmethod
    def get_with_errors(cls):
        """Retorna fontes com erro"""
        return cls.objects.filter(status=cls.StatusChoices.ERROR)

    @classmethod
    def get_needs_processing(cls):
        """Retorna fontes que precisam ser processadas (pending + reprocess)"""
        return cls.objects.filter(
            status__in=[cls.StatusChoices.PENDING, cls.StatusChoices.REPROCESS]
        )

    @classmethod
    def process_xmls(
        cls,
        user,
        load_article,
        status__in=None,
        force_update=False,
        auto_solve_pid_conflict=False,
    ):
        if force_update:
            items = cls.objects.iterator()
        else:
            params = {}
            params["status__in"] = status__in or [
                cls.StatusChoices.PENDING,
                cls.StatusChoices.REPROCESS,
            ]

            items = cls.objects.select_related(
                "pid_provider_xml",
                "article",
            ).filter(
                Q(pid_provider_xml__isnull=True)
                | Q(file__isnull=True)
                | Q(article__isnull=True)
                | Q(article__valid__in=[None, False])
                | Q(**params),
            )
        logging.info(f"Process article source total: {items.count()}")
        for item in items:
            item.process_xml(user, load_article, force_update, auto_solve_pid_conflict)

    def process_xml(
        self, user, load_article, force_update=False, auto_solve_pid_conflict=False
    ):
        """
        Processa um arquivo XML de artigo científico, criando ou atualizando os dados necessários.

        Este método gerencia todo o fluxo de processamento de um XML de artigo, incluindo:
        - Download/criação do arquivo XML se necessário
        - Geração de PID (Persistent Identifier) através do PidProvider
        - Criação do objeto Article associado
        - Atualização do status conforme o resultado do processamento

        Args:
            user: Usuário responsável pelo processamento
            load_article: Função callback para carregar/criar o artigo a partir do XML
            force_update (bool): Se True, força a atualização mesmo se os dados já existem
            auto_solve_pid_conflict (bool): Se True, resolve automaticamente conflitos de PID

        Raises:
            ValueError: Se a URL não estiver definida

        Note:
            O método atualiza os seguintes atributos do objeto:
            - status: Estado do processamento (PENDING, COMPLETED, ERROR)
            - file: Arquivo XML baixado/criado
            - pid_provider_xml: Objeto PidProviderXML associado
            - article: Objeto Article criado
            - detail: Lista com detalhes do processamento
        """

        try:
            # Valida se existe URL para processar
            if not self.url:
                raise ValueError(_("URL is required"))

            if not force_update and self.article and self.article.valid:
                if self.status != ArticleSource.StatusChoices.COMPLETED:
                    self.mark_as_completed()
                return

            # Lista para armazenar detalhes do processamento
            detail = []

            # Define status inicial como pendente
            self.status = ArticleSource.StatusChoices.PENDING

            # Verifica se precisa criar/baixar o arquivo XML
            if (
                force_update
                or not self.file
                or not self.file.path
                or not os.path.isfile(self.file.path)
            ):
                logging.info("create file")
                detail.append("create file")
                self.create_file()  # Método que baixa/cria o arquivo XML
                detail.append("created file")

            self.set_pid_provider_xml(
                user, detail, force_update, auto_solve_pid_conflict
            )
            if not self.pid_provider_xml or not self.pid_provider_xml.v3:
                raise ValueError("Missing pid_provider_xml")

            # Se tem v3, pode criar o artigo
            if force_update or not self.article or not self.article.valid:
                logging.info("create article")
                detail.append("create article")

                # Chama a função para carregar/criar o artigo
                self.article = load_article(
                    user=user,
                    xml=None,
                    file_path=self.file.path,
                    v3=self.pid_provider_xml.v3,
                    pp_xml=self.pid_provider_xml,
                )
                # Verifica se o artigo foi criado com sucesso
                if self.article.valid:
                    detail.append("created valid article")
                    self.mark_as_completed()  # Marca o processamento como concluído
                else:
                    detail.append("created incomplete article")

            logging.info((self.article, self.pid_provider_xml))
            self.detail = detail
            self.save()

        except Exception as e:
            # Registra a exceção no log
            logging.exception(e)

            # Obtém informações detalhadas da exceção
            exc_type, exc_value, exc_traceback = sys.exc_info()

            # Adiciona informações do erro aos detalhes
            detail.append(str({"error_type": str(type(e)), "error_message": str(e)}))
            self.detail = detail

            # Marca o processamento como erro
            self.mark_as_error()

    def set_pid_provider_xml(self, user, detail, force_update, auto_solve_pid_conflict):
        # Verifica se precisa gerar o PID para o XML
        if force_update or not self.pid_provider_xml:
            logging.info("create pid_provider_xml")
            detail.append("create pid_provider_xml")

            # Instancia o provedor de PIDs
            pp = PidProvider()

            # Solicita PID para o arquivo XML/ZIP
            responses = pp.provide_pid_for_xml_zip(
                self.file.path,
                user,
                filename=self.sps_pkg_name,
                origin_date=self.source_date,
                force_update=force_update,
                is_published=True,
                auto_solve_pid_conflict=auto_solve_pid_conflict,
            )

            # Obtém a primeira resposta (assumindo apenas uma)
            response = list(responses)[0]
            v3 = response.get("v3")

            if v3:
                # Associa o PidProviderXML ao ArticleSource
                self.pid_provider_xml = PidProviderXML.objects.get(v3=v3)
                detail.append("created pid_provider_xml")
            else:
                # Registra erro se não conseguiu obter v3
                detail.append(str(response))


class ArticleExport(CommonControlField):
    """
    Controla exportações de artigos para diferentes bases de dados (articlemeta, crossref, pubmed)
    """
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="exports",
        verbose_name=_("Article")
    )
    export_type = models.CharField(
        max_length=50,
        choices=[
            ('articlemeta', 'ArticleMeta'),
            ('crossref', 'CrossRef'),
            ('pubmed', 'PubMed'),
        ],
        verbose_name=_("Export Type")
    )
    exported_at = models.DateTimeField(auto_now_add=True)
    collection = models.ForeignKey(
        'collection.Collection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Collection")
    )
    
    class Meta:
        unique_together = ['article', 'export_type', 'collection']
        indexes = [
            models.Index(fields=['article', 'export_type']),
            models.Index(fields=['exported_at']),
        ]
    
    def __str__(self):
        return f"{self.article.pid_v3} -> {self.export_type}"

    @classmethod
    def mark_as_exported(cls, article, export_type, collection, user=None):
        """Marca um artigo como exportado"""
        obj, created = cls.objects.get_or_create(
            article=article,
            export_type=export_type,
            collection=collection,
            defaults={'creator': user}
        )
        if not created:
            obj.exported_at = datetime.now()
            obj.updated_by = user
            obj.save()
        return obj

    @classmethod
    def is_exported(cls, article, export_type, collection):
        """Verifica se um artigo já foi exportado"""
        return cls.objects.filter(
            article=article,
            export_type=export_type,
            collection=collection
        ).exists()
