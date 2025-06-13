import os
import sys
import logging
from datetime import datetime

from django.core.files.base import ContentFile
from django.db import IntegrityError, models
from django.utils.translation import gettext as _
from django_prometheus.models import ExportModelOperationsMixin

from packtools.sps.formats import pubmed, pmc, crossref
from packtools.sps.pid_provider.xml_sps_lib import generate_finger_print

from legendarium.formatter import descriptive_format
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from article.forms import ArticleForm, ArticleFormatForm
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
from institution.models import Publisher, Sponsor
from issue.models import Issue, TocSection
from journal.models import Journal, SciELOJournal
from pid_provider.provider import PidProvider
from researcher.models import InstitutionalAuthor, Researcher
from tracker.models import UnexpectedEvent
from vocabulary.models import Keyword



class Article(ExportModelOperationsMixin('article'), CommonControlField, ClusterableModel):
    pid_v2 = models.CharField(_("PID V2"), max_length=23, null=True, blank=True)
    pid_v3 = models.CharField(_("PID V3"), max_length=23, null=True, blank=True, unique=True)
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
        Publisher,
        verbose_name=_("Publisher"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    valid = models.BooleanField(default=False, blank=True, null=True)

    autocomplete_search_field = "sps_pkg_name"

    def autocomplete_label(self):
        return str(self)

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
        AutocompletePanel("license_statements"),
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
        InlinePanel("formats", label=_("Formats")),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_ids, heading=_("Identification")),
            ObjectList(panels_languages, heading=_("Data with language")),
            ObjectList(panels_researchers, heading=_("Researchers")),
            ObjectList(panels_institutions, heading=_("Publisher and Sponsors")),
            ObjectList(panels_formats, heading=_("Formats")),
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
        return self.sps_pkg_name or self.pid_v3 or f"{self.doi.first()}" or self.titles

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
    def root_path(self):
        items = [
            self.journal.issn_electronic or self.journal.issn_print,
            self.issue.year,
        ]
        return "/".join([item for item in items if item])

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

    def generate_formats(self, user=None):
        user = user or self.updated_by
        ArticleFormat.create_or_update(user, self, "pmc")

        for item in self.journal.indexed_at.all():
            ArticleFormat.create_or_update(user, self, item.acronym)

    base_form_class = ArticleForm


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
            "article", *instance.article.sps_pkg_name.split("-"), instance.format_name, filename
        )
    except AttributeError:
        return os.path.join("article", instance.article.root_path, instance.article.pid_v3, instance.format_name, filename)


class ArticleFormat(CommonControlField):
    """
    Armazena cada instância de formato gerado para um Article.
    """

    # Mapeia nome de formato → função pipeline
    PIPELINES = {
        "crossref": crossref.pipeline_crossref,
        "pubmed":   pubmed.pipeline_pubmed,
        "pmc":      pmc.pipeline_pmc,
    }

    article = ParentalKey(
        Article,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="formats",
    )
    format_name = models.CharField(
        "Article Format", max_length=20, null=True, blank=True
    )
    version = models.PositiveIntegerField(null=True, blank=True)
    file = models.FileField(
        "File", null=True, blank=True, upload_to=lambda inst, fn: inst.article_directory_path(fn)
    )
    report = models.JSONField(null=True, blank=True)
    valid = models.BooleanField(null=True, blank=True)
    finger_print = models.CharField(max_length=64, null=True, blank=True)

    base_form_class = ArticleFormatForm
    panels = [
        AutocompletePanel("article"),
        FieldPanel("format_name"),
        FieldPanel("version"),
        FieldPanel("file"),
    ]

    class Meta:
        unique_together = [("article", "format_name", "version")]
        indexes = [
            models.Index(fields=["article"]),
            models.Index(fields=["format_name"]),
            models.Index(fields=["version"]),
        ]

    def __str__(self):
        return f"{self.article} [{self.format_name} v{self.version}]"

    def save_file(self, filename, content):
        """
        Salva o conteúdo num FileField, só se tiver fingerprint diferente.
        """
        fp = generate_finger_print(content)
        if fp != self.finger_print:
            try:
                self.file.delete(save=False)
            except Exception:
                pass
            self.file.save(f"{filename}.xml", ContentFile(content), save=False)
            self.finger_print = fp
            self.save()

    def _handle_error(self, exception):
        """
        Registra UnexpectedEvent e marca este formato como inválido.
        """
        exc_type, _, exc_tb = sys.exc_info()
        ev = UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_tb,
            detail={
                "function": "ArticleFormat._generate",
                "format_name": self.format_name,
                "article_pid_v3": self.article.pid_v3,
            },
        )
        self.report = ev.data
        self.valid = False
        self.save()

    def _generate(self, user, pipeline_func):
        """
        Executa o pipeline e salva o resultado, ou trata erro.
        """
        try:
            xmltree = self.article.xmltree
            content = pipeline_func(xmltree)
            if not content:
                raise ValueError(f"Formato '{self.format_name}' retornou conteúdo vazio.")
            # salva, limpa relatório e marca válido
            self.save_file(self.article.sps_pkg_name, content)
            self.report = None
            self.valid = True
            self.updated_by = user
            self.save()
        except Exception as e:
            self._handle_error(e)

    @classmethod
    def generate_formats(cls, user, article, indexed_check=False, formats=None):
        """
        Gera todos os formatos configurados em PIPELINES para o dado artigo.
        Se indexed_check=True, só gera aqueles em que article.is_indexed_at(fmt) é True.
        """
        targets = formats or cls.PIPELINES.keys()
        for fmt in targets:
            if fmt not in cls.PIPELINES:
                continue
            if indexed_check and not article.is_indexed_at(fmt):
                continue

            obj, created = cls.objects.get_or_create(
                article=article,
                format_name=fmt,
                version=1,
                defaults={"creator": user},
            )
            if not created:
                obj.updated_by = user
                obj.save()
            obj._generate(user, cls.PIPELINES[fmt])
