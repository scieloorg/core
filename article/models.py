import logging
import os
import sys
import traceback
from datetime import datetime
from functools import lru_cache, cached_property

from django.core.files.base import ContentFile
from django.db import IntegrityError, models
from django.db.models import Q, Count, Min
from django.db.utils import DataError
from django.utils import timezone
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
from article.utils.url_builder import ArticleURLBuilder
from collection.models import Collection
from core.forms import CoreAdminModelForm
from core.models import CommonControlField  # Ajuste o import conforme sua estrutura
from core.models import (
    BaseExporter,
    BaseLegacyRecord,
    FlexibleDate,
    Language,
    License,
    LicenseStatement,
    TextLanguageMixin,
)
from core.utils.utils import NonRetryableError, fetch_data
from doi.models import DOI
from doi_manager.models import CrossRefConfiguration
from institution.models import Publisher, Sponsor
from issue.models import Issue, TocSection
from journal.models import Journal, SciELOJournal
from pid_provider.choices import PPXML_STATUS_DONE
from pid_provider.models import PidProviderXML
from pid_provider.provider import PidProvider
from researcher.models import InstitutionalAuthor, Researcher
from tracker.models import BaseEvent, EventSaveError, UnexpectedEvent
from vocabulary.models import Keyword


class AMArticle(BaseLegacyRecord):
    """
    Modelo que representa a coleta de dados de Issue na API Article Meta.

    from:
        https://articlemeta.scielo.org/api/v1/issue/?collection={collection}&code={code}"
    """

    pid = models.CharField(
        _("PID"),
        max_length=23,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Legacy article")
        verbose_name_plural = _("Legacy articles")
        indexes = [
            models.Index(
                fields=[
                    "pid",
                ]
            ),
        ]


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
    legacy_article = models.ManyToManyField(AMArticle)
    is_public = models.BooleanField(default=False, blank=True, null=True)

    base_form_class = CoreAdminModelForm

    # Metadados principais do artigo
    panels_identification = [
        FieldPanel("is_public"),
        FieldPanel("data_status"),
        FieldPanel("valid"),
        FieldPanel("pid_v2", read_only=True),
        FieldPanel("pid_v3", read_only=True),
        AutocompletePanel("doi", read_only=True),
        AutocompletePanel("legacy_article"),
    ]

    # Informações de publicação
    panels_publication = [
        AutocompletePanel("journal", read_only=True),
        AutocompletePanel("issue", read_only=True),
        FieldPanel("pub_date_year", read_only=True),
        FieldPanel("pub_date_month", read_only=True),
        FieldPanel("pub_date_day", read_only=True),
        FieldPanel("first_page", read_only=True),
        FieldPanel("last_page", read_only=True),
        FieldPanel("elocation_id", read_only=True),
    ]

    # Conteúdo e classificação
    panels_content = [
        FieldPanel("article_type", read_only=True),
        AutocompletePanel("toc_sections", read_only=True),
        AutocompletePanel("languages", read_only=True),
        AutocompletePanel("titles", read_only=True),
        InlinePanel("abstracts", label=_("Abstract")),
        AutocompletePanel("keywords", read_only=True),
    ]

    # Autoria e colaboração
    panels_authorship = [
        AutocompletePanel("researchers", read_only=True),
        AutocompletePanel("collab", read_only=True),
    ]

    # Licenciamento e financiamento
    panels_rights_funding = [
        AutocompletePanel("license", read_only=True),
        # AutocompletePanel("license_statements"),
        AutocompletePanel("fundings", read_only=True),
    ]
    panels_errors = [
        FieldPanel("errors", read_only=True),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_identification, heading=_("Identification")),
            ObjectList(panels_publication, heading=_("Publication Details")),
            ObjectList(panels_content, heading=_("Content & Classification")),
            ObjectList(panels_authorship, heading=_("Authors & Collaborators")),
            ObjectList(panels_rights_funding, heading=_("Rights & Funding")),
            ObjectList(panels_errors, heading=_("Errors")),
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

    @cached_property
    def xml_with_pre(self):
        try:
            return self.pp_xml.xml_with_pre
        except AttributeError:
            return PidProviderXML.get_xml_with_pre(self.pid_v3)

    @property
    def xmltree(self):
        try:
            return self.xml_with_pre.xmltree
        except AttributeError:
            return PidProvider.get_xmltree(self.pid_v3)

    @property
    def abstracts(self):
        return DocumentAbstract.objects.filter(article=self)

    @cached_property
    def collections(self):
        if self.journal:
            cols = []
            for item in self.journal.scielojournal_set.all().select_related(
                "collection"
            ):
                cols.append(item.collection)
            return cols
        return []

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
            "suppl": self.issue.supplement,
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
        year = self.pub_date_year or ""
        month = self.pub_date_month or ""
        day = self.pub_date_day or ""

        if year and month and day:
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

        elif year and month:
            return f"{year}-{month.zfill(2)}"

        else:
            return year

    @classmethod
    def get_versions(
        cls,
        pid_v3=None,
        sps_pkg_name=None,
    ):
        if not pid_v3 and not sps_pkg_name:
            raise ValueError("Article requires params: pid_v3 or sps_pkg_name")
        q = Q()
        if sps_pkg_name:
            q |= Q(sps_pkg_name=sps_pkg_name)
        if pid_v3:
            q |= Q(pid_v3=pid_v3)
        return (
            cls.objects.filter(q)
            .exclude(
                data_status__in=choices.DATA_STATUS_EXCLUSION_LIST,
            )
            .order_by("-updated")
        )

    @classmethod
    def get(
        cls,
        pid_v3=None,
        sps_pkg_name=None,
    ):
        if not pid_v3 and not sps_pkg_name:
            raise ValueError("Article requires params: pid_v3 or sps_pkg_name")
        try:
            return cls.objects.get(sps_pkg_name=sps_pkg_name, pid_v3=pid_v3)
        except cls.DoesNotExist:
            versions = cls.get_versions(pid_v3=pid_v3, sps_pkg_name=sps_pkg_name)
            total = versions.count()
            if total == 0:
                raise cls.DoesNotExist
            if total == 1:
                return versions.first()
            raise cls.MultipleObjectsReturned(
                f"Found {total} Article {pid_v3} {sps_pkg_name}"
            )

    @classmethod
    def create(
        cls,
        user,
        pid_v3=None,
        sps_pkg_name=None,
    ):
        try:
            logging.info(f"create: {pid_v3} {sps_pkg_name}")
            obj = cls()
            obj.pid_v3 = pid_v3
            obj.sps_pkg_name = sps_pkg_name
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(pid_v3=pid_v3, sps_pkg_name=sps_pkg_name)

    @classmethod
    def create_or_update(
        cls,
        user,
        pid_v3=None,
        sps_pkg_name=None,
    ):
        logging.info(f"get_or_create: {pid_v3} {sps_pkg_name}")
        try:
            return cls.get(pid_v3=pid_v3, sps_pkg_name=sps_pkg_name)
        except cls.DoesNotExist:
            return cls.create(user=user, pid_v3=pid_v3, sps_pkg_name=sps_pkg_name)
        except cls.MultipleObjectsReturned:
            return cls.get_versions(pid_v3=pid_v3, sps_pkg_name=sps_pkg_name).first()

    @classmethod
    def get_or_create(
        cls,
        pid_v3=None,
        user=None,
        sps_pkg_name=None,
    ):
        return cls.create_or_update(user=user, pid_v3=pid_v3, sps_pkg_name=sps_pkg_name)

    def complete_data(self, pp_xml):
        save = False
        if pp_xml:
            if not self.sps_pkg_name:
                self.sps_pkg_name = pp_xml.pkg_name
                save = True
            if not self.pp_xml:
                self.pp_xml = pp_xml
                save = True

        if not self.article_license:
            try:
                self.article_license = self.license.license_type
                save = True
            except (TypeError, ValueError, AttributeError):
                try:
                    self.article_license = (
                        self.license_statements.first().license.license_type
                    )
                    save = True
                except (TypeError, ValueError, AttributeError):
                    pass
        if save:
            self.save()

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

    def create_legacy_keys(self, collection_acron_list):
        if self.legacy_article.count() == 0:

            query_set = self.journal.scielojournal_set
            logging.info(f"scileojournal total: {query_set.count()}")
            if query_set.count() == 1:
                if self.pid_v2:
                    am_article = AMArticle.create_or_update(
                        self.pid_v2,
                        query_set.first().collection,
                        None,
                        self.updated_by,
                    )
                    self.legacy_article.add(am_article)

    def get_legacy_keys(self, collection_acron_list=None, is_active=None):
        self.create_legacy_keys(collection_acron_list)
        params = {}
        if collection_acron_list:
            params["collection__acron3__in"] = collection_acron_list
        logging.info(
            self.legacy_article.filter(
                collection__is_active=is_active, **params
            ).count()
        )
        for item in self.legacy_article.filter(
            collection__is_active=is_active, **params
        ):
            yield item.legacy_keys

    def select_collections(self, collection_acron_list=None, is_activate=None):
        if not self.journal:
            raise ValueError(f"{self} has no journal")
        return self.journal.select_collections(collection_acron_list, is_activate)

    def select_journals(self, collection_acron_list=None):
        if not self.journal:
            raise ValueError(f"{self} has no journal")
        return self.journal.select_items(collection_acron_list)

    @classmethod
    def select_items(
        cls,
        collection_acron_list=None,
        journal_acron_list=None,
        from_pub_year=None,
        until_pub_year=None,
        volume=None,
        number=None,
        supplement=None,
        from_updated_date=None,
        until_updated_date=None,
        data_status_list=None,
        valid=None,
        pp_xml__isnull=None,
        sps_pkg_name__isnull=None,
        article_license__isnull=None,
    ):
        params = {}
        if collection_acron_list:
            params["journal__scielojournal__collection__acron__in"] = (
                collection_acron_list
            )
        if journal_acron_list:
            params["journal__scielojournal__journal_acron__in"] = journal_acron_list

        if from_pub_year:
            params["issue__year__gte"] = from_pub_year
        if until_pub_year:
            params["issue__year__lte"] = until_pub_year

        if from_updated_date:
            params["updated_date__gte"] = from_updated_date
        if until_updated_date:
            params["updated_date__lte"] = until_updated_date

        if data_status_list:
            params["data_status__in"] = data_status_list

        if volume:
            params["issue__volume"] = volume
        if number:
            params["issue__number"] = number
        if supplement:
            params["issue__supplement"] = supplement

        q = Q()
        if valid is not None:
            q |= Q(valid=valid)
        if pp_xml__isnull is not None:
            q |= Q(pp_xml__isnull=pp_xml__isnull)
        if sps_pkg_name__isnull is not None:
            q |= Q(sps_pkg_name__isnull=sps_pkg_name__isnull)
        if article_license__isnull is not None:
            q |= Q(article_license__isnull=article_license__isnull)
        return cls.objects.filter(q, **params)

    @classmethod
    def select_journal_articles(cls, journal=None, issns=None):
        if not issns and not journal:
            raise ValueError(
                "Article.select_journal_articles requires issns or journal param"
            )
        if journal:
            return cls.objects.filter(journal=journal)
        return cls.objects.filter(
            Q(journal__official__issn_print__in=issns)
            | Q(journal__official__issn_electronic__in=issns)
        )

    @cached_property
    def langs(self):
        return [lang.code2 for lang in self.languages.all()]

    def get_article_urls(self, collection_acron_list=None, collection=None, fmt=None):
        params = {}
        if fmt:
            params["fmt"] = fmt
        if collection:
            params["collection"] = collection
        if collection_acron_list:
            params["collection__acron3__in"] = collection_acron_list
        for item in self.article_availability.filter(available=True, **params):
            yield item.data

    def check_availability(
        self,
        user,
        collection_acron_list=None,
        timeout=None,
        is_activate=None,
        force_update=False,
    ):
        try:
            if not self.is_pp_xml_valid():
                return False
            if not force_update and self.is_available(collection_acron_list):
                return True

            event = None
            event = self.add_event(user, _("check availability"))
            for collection in self.select_collections(
                collection_acron_list,
                is_activate=is_activate,
            ):
                url_builder = ArticleURLBuilder(
                    collection.domain,
                    self.journal.scielojournal_set.filter(collection=collection)
                    .first()
                    .journal_acron,
                    self.pid_v2,
                    self.pid_v3,
                )
                for item in url_builder.get_urls(self.langs):
                    ArticleAvailability.create_or_update(
                        user,
                        self,
                        collection=collection,
                        url=item["url"],
                        fmt=item["format"],
                        lang=item.get("lang"),
                        timeout=timeout,
                    )
            event.finish(
                completed=True,
                detail=ArticleAvailability.get_stats(self),
            )
            return self.is_available(collection_acron_list)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if event:
                event.finish(completed=False, exceptions=traceback.format_exc())

            UnexpectedEvent.create(
                item=str(self),
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    function="article.models.Article.check_availability",
                ),
            )

    def is_available(self, collection_acron_list=None, fmt=None):
        if not self.is_pp_xml_valid():
            return False
        for item in self.get_article_urls(
            collection_acron_list=collection_acron_list, fmt=fmt
        ):
            if self.data_status != choices.DATA_STATUS_PUBLIC or not self.is_public:
                self.data_status = choices.DATA_STATUS_PUBLIC
                self.is_public = True
                self.save()
            self.pp_xml.mark_as_done()
            return True
        self.pp_xml.mark_as_waiting()
        return False

    def add_event(self, user, name):
        return ArticleEvent.create(user, self, name)

    @classmethod
    def mark_items_as_public(cls, journal=None, force_update=False, user=None):
        # DATA_STATUS_DELETED, DATA_STATUS_MOVED, DATA_STATUS_INVALID, DATA_STATUS_DUPLICATED,
        if force_update:
            exclusion_list = []
        else:
            exclusion_list = choices.DATA_STATUS_EXCLUSION_LIST + [
                choices.DATA_STATUS_PUBLIC
            ]
        for item in (
            cls.select_journal_articles(journal=journal)
            .exclude(
                data_status__in=exclusion_list,
            )
            .iterator()
        ):
            item.check_availability(
                user=user or item.updated_by, force_update=force_update
            )

    @classmethod
    def mark_items_as_invalid(cls, journal=None):
        qs = cls.select_journal_articles(journal=journal)
        if qs.count() == 0:
            return
        for item in qs.iterator():
            item.is_pp_xml_valid()

    def is_pp_xml_valid(self):
        if not self.pp_xml:
            try:
                self.pp_xml = PidProviderXML.objects.get(v3=self.pid_v3)
            except PidProviderXML.DoesNotExist:
                pass
        if not self.pp_xml or not self.pp_xml.xml_with_pre:
            if self.data_status != choices.DATA_STATUS_INVALID:
                self.data_status = choices.DATA_STATUS_INVALID
                self.save()
            return None
        return self.id

    @classmethod
    def find_duplicated_pkg_names(cls, journal):
        # Busca em ambos os campos de ISSN
        duplicates = (
            cls.objects.filter(journal=journal)
            .exclude(sps_pkg_name__isnull=True)
            .exclude(sps_pkg_name="")
            .exclude(data_status=choices.DATA_STATUS_DUPLICATED)
            .values("sps_pkg_name")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )
        return list(item["sps_pkg_name"] for item in duplicates)

    @classmethod
    def mark_items_as_duplicated(cls, journal):
        """
        Corrige todos os artigos marcados como DATA_STATUS_DUPLICATED com base nos ISSNs fornecidos.

        Args:
            issns: Lista de ISSNs para verificar duplicatas.
            user: Usuário que está executando a operação.
        """
        article_duplicated_pkg_names = cls.find_duplicated_pkg_names(journal)
        if not article_duplicated_pkg_names:
            return
        cls.objects.filter(sps_pkg_name__in=article_duplicated_pkg_names).exclude(
            data_status=choices.DATA_STATUS_DUPLICATED
        ).update(
            data_status=choices.DATA_STATUS_DUPLICATED,
        )
        return article_duplicated_pkg_names

    @classmethod
    def deduplicate_items(cls, user, journal):
        """
        Corrige todos os artigos marcados como DATA_STATUS_DUPLICATED com base nos ISSNs fornecidos.

        Args:
            issns: Lista de ISSNs para verificar duplicatas.
            user: Usuário que está executando a operação.
        """
        article_duplicated_pkg_names = cls.find_duplicated_pkg_names(journal)
        for pkg_name in article_duplicated_pkg_names:
            cls.fix_duplicated_pkg_name(pkg_name, user)
        return article_duplicated_pkg_names

    @classmethod
    def fix_duplicated_pkg_name(cls, pkg_name, user):
        """
        Corrige artigos marcados como DATA_STATUS_DUPLICATED com base no pkg_name fornecido.

        Args:
            pkg_name: Nome do pacote para verificar duplicatas.
            user: Usuário que está executando a operação.

        Returns:
            int: Número de artigos atualizados.
        """
        try:
            articles = cls.objects.filter(sps_pkg_name=pkg_name).exclude(
                data_status=choices.DATA_STATUS_DUPLICATED
            )
            if articles.count() <= 1:
                return articles.first()

            # Mantém o artigo mais recente como o correto
            not_available_articles = []
            for item in articles.order_by("-updated"):
                if item.check_availability(user, force_update=True):
                    return item
                else:
                    not_available_articles.append(item)

            not_available_articles[0].data_status = choices.DATA_STATUS_DEDUPLICATED
            not_available_articles[0].save()
            return not_available_articles[0]

        except Exception as exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=exception,
                exc_traceback=exc_traceback,
                action="article.models.Article.fix_duplicated_pkg_name",
                detail=pkg_name,
            )


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
    detail = models.JSONField(null=True, blank=True, default=None)
    am_article = models.ForeignKey(
        AMArticle,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Legacy Article"),
        help_text=_("Related Legacy Article instance"),
    )
    base_form_class = CoreAdminModelForm

    panels = [
        FieldPanel("url", read_only=True),
        FieldPanel("file", read_only=True),
        FieldPanel("source_date", read_only=True),
        FieldPanel("status"),
        FieldPanel("am_article", read_only=True),
        FieldPanel("pid_provider_xml", read_only=True),
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
    def create(cls, user, url=None, source_date=None, am_article=None):
        if not url:
            raise ValueError("ArticleSource.create requires url")

        try:
            obj = cls()
            obj.creator = user
            obj.url = url
            obj.source_date = source_date
            obj.am_article = am_article
            obj.status = cls.StatusChoices.PENDING
            obj.save()
            try:
                obj.request_xml(detail=[])
            except Exception as e:
                pass
            return obj
        except IntegrityError:
            return cls.get(url=url)

    @classmethod
    def create_or_update(
        cls, user, url=None, source_date=None, am_article=None, force_update=None
    ):
        try:
            logging.info(
                f"ArticleSource.create_or_update {url} {source_date} {am_article} {force_update}"
            )
            obj = cls.get(url=url)

            if (
                force_update
                or (source_date and source_date != obj.source_date)
                or (am_article and am_article != obj.am_article)
                or not obj.file
                or not obj.file.path
                or not os.path.isfile(obj.file.path)
            ):
                logging.info(f"updating source: {(source_date, obj.source_date)}")
                logging.info(f"updating am_article: {(am_article, obj.am_article)}")
                logging.info(
                    f"updating file: {not obj.file or not obj.file.path or not os.path.isfile(obj.file.path)}"
                )
                obj.request_xml()
                obj.updated_by = user
                obj.source_date = source_date
                obj.am_article = am_article
                obj.status = cls.StatusChoices.REPROCESS
                obj.save()

        except cls.DoesNotExist:
            obj = cls.create(
                user, url=url, source_date=source_date, am_article=am_article
            )
        return obj

    @cached_property
    def sps_pkg_name(self):
        try:
            xml_with_pre = list(XMLWithPre.create(path=self.file.path))[0]
        except:
            xml_with_pre = list(XMLWithPre.create(uri=self.url))[0]
        return xml_with_pre.sps_pkg_name

    def request_xml(self, detail=None, force_update=False):
        if not self.url:
            raise ValueError("URL is required")

        if (
            not self.file
            or not self.file.path
            or not os.path.isfile(self.file.path)
            or force_update
        ):
            if detail:
                detail.append("create file")

            logging.info(f"ArticleSource.request_xml for {self.url}")
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
    def get_queryset_to_complete_data(
        cls,
        from_date=None,
        until_date=None,
        force_update=None,
    ):
        params = {}
        if from_date:
            params["updated__gte"] = from_date
        if until_date:
            params["updated__lte"] = until_date

        if force_update:
            return cls.objects.filter(**params)

        return cls.objects.filter(
            Q(pid_provider_xml__isnull=True) | Q(file__isnull=True),
            **params,
        )

    @property
    def is_completed(self):
        if not self.pid_provider_xml:
            return False
        if not self.am_article:
            return False
        if self.status != ArticleSource.StatusChoices.COMPLETED:
            self.status = ArticleSource.StatusChoices.COMPLETED
            self.save()
        return True

    def complete_data(self, user, force_update=False, auto_solve_pid_conflict=False):
        """
        Processa um arquivo XML de artigo científico, criando ou atualizando os dados necessários.

        Este método gerencia todo o fluxo de processamento de um XML de artigo, incluindo:
        - Download/criação do arquivo XML se necessário
        - Geração de PID (Persistent Identifier) através do PidProvider

        Args:
            user: Usuário responsável pelo processamento
            force_update (bool): Se True, força a atualização mesmo se os dados já existem
            auto_solve_pid_conflict (bool): Se True, resolve automaticamente conflitos de PID

        Raises:
            ValueError: Se a URL não estiver definida

        Note:
            O método atualiza os seguintes atributos do objeto:
            - status: Estado do processamento (PENDING, COMPLETED, ERROR)
            - file: Arquivo XML baixado/criado
            - pid_provider_xml: Objeto PidProviderXML associado
            - detail: Lista com detalhes do processamento
        """

        try:
            # Lista para armazenar detalhes do processamento
            detail = []
            if not force_update:
                if self.is_completed:
                    return

            # Define status inicial como pendente
            self.status = ArticleSource.StatusChoices.PENDING

            # baixa/cria o arquivo XML
            self.request_xml(detail, force_update)

            pid_v3 = self.get_or_create_pid_v3(
                user, detail, force_update, auto_solve_pid_conflict
            )
            self.mark_as_completed()  # Marca o processamento como concluído
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

    def get_or_create_pid_v3(self, user, detail, force_update, auto_solve_pid_conflict):
        if self.pid_provider_xml:
            if not force_update:
                return self.pid_provider_xml.v3
        try:
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
                detail.append("set pid_provider_xml")
                return v3
            else:
                # Registra erro se não conseguiu obter v3
                detail.append(str(response))
        except Exception as e:
            logging.exception(e)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            unexpected_event = UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    function="article.models.ArticleSource.get_or_create_pid_v3",
                    article_source_id=self.id,
                    sps_pkg_name=self.sps_pkg_name,
                    url=self.url,
                ),
            )
            detail.append(str(unexpected_event.data))
            raise e


class ArticleAvailability(CommonControlField):
    collection = models.ForeignKey(
        Collection,
        verbose_name=_("Collection"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    lang = models.ForeignKey(
        Language,
        verbose_name=_("Language"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    article = ParentalKey(
        Article,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="article_availability",
    )
    url = models.URLField(max_length=500, unique=True)
    available = models.BooleanField(default=False)
    fmt = models.CharField(_("Format"), max_length=4, null=True, blank=True)
    error = models.CharField(max_length=40, null=True, blank=True)

    panels = [FieldPanel("url"), FieldPanel("available", read_only=True)]

    @classmethod
    def get(cls, article, url):
        return cls.objects.get(article=article, url=url)

    @classmethod
    def create(
        cls,
        user,
        article,
        collection,
        url,
        fmt,
        lang,
        timeout=None,
    ):
        try:
            obj = cls(
                article=article,
                collection=collection,
                url=url,
                fmt=fmt,
                lang=lang,
                creator=user,
            )
            obj.check_availability(timeout)
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(article, url)

    @classmethod
    def create_or_update(
        cls,
        user,
        article,
        collection,
        url,
        fmt,
        lang,
        timeout=None,
    ):
        try:
            if lang:
                lang = Language.objects.filter(code2=lang).first()
            obj = cls.get(article=article, url=url)
            obj.fmt = fmt
            obj.lang = lang
            obj.collection = collection
            obj.update(user, timeout)
            return obj
        except cls.DoesNotExist:
            return cls.create(
                user=user,
                article=article,
                collection=collection,
                url=url,
                fmt=fmt,
                lang=lang,
                timeout=timeout,
            )

    def check_availability(self, timeout=None):
        try:
            available = check_url(self.url, timeout)
            error = None
        except Exception as e:
            available = False
            error = str(type(e).__name__)
        if available != self.available or error != self.error:
            self.available = available
            self.error = error
            self.updated = timezone.now()
        return available

    def update(self, user, timeout=None):
        self.check_availability(timeout)
        self.updated_by = user
        self.save()

    @property
    def data(self):
        return {
            "format": self.fmt,
            "lang": self.lang and self.lang.code2,
            "url": self.url,
            "available": self.available,
            "last_checked": self.updated.isoformat() if self.updated else None,
        }

    @classmethod
    def get_stats(cls, article, **filters):
        """
        Retorna relatório com total, total indisponível e dados dos itens indisponíveis.

        Args:
            article: Instância do Article ou ID do artigo (opcional)
            **filters: Filtros adicionais do Django ORM

        Returns:
            dict: Relatório de indisponibilidade com dados completos
        """
        # Construir queryset base
        queryset = cls.objects.filter(article=article, **filters)

        # Contar totais
        total = queryset.count()
        unavailable_queryset = queryset.filter(available=False)
        total_unavailable = unavailable_queryset.count()

        # Obter dados completos dos itens indisponíveis
        unavailable_items = []
        for item in queryset.filter(available=False):
            unavailable_items.append(item.data)

        return {
            "total": total,
            "total_available": total - total_unavailable,
            "availability_rate": (
                round(((total - total_unavailable) / total * 100), 2)
                if total > 0
                else 0
            ),
            "unavailable_items": unavailable_items,
        }


def check_url(url, timeout=None):
    try:
        fetch_data(url, timeout=timeout or 30)
        return True
    except Exception as e:
        raise


class ArticleEvent(BaseEvent, CommonControlField, Orderable):
    """
    Registra eventos relacionados a um artigo específico.
    Herda de BaseEvent (name, detail, created) e CommonControlField (creator, updated_by, etc)
    """

    article = ParentalKey(
        Article,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("Article"),
    )

    class Meta:
        ordering = ["-created", "-id"]  # Mais recente primeiro
        indexes = [
            models.Index(fields=["article", "-created"]),
            models.Index(fields=["name"]),
            models.Index(fields=["created"]),
        ]
        verbose_name = _("Article Event")
        verbose_name_plural = _("Article Events")

    panels = [
        FieldPanel("name"),
        FieldPanel("detail"),
        FieldPanel("created", read_only=True),
    ]

    def __str__(self):
        return f"{self.name} - {self.created.strftime('%Y-%m-%d %H:%M:%S')}"

    @classmethod
    def create(cls, user, article, name, detail=None):
        """
        Cria um novo evento para o artigo.

        Args:
            article: Instância do Article
            name: Nome do evento (ex: "validation_started", "export_completed")
            detail: Detalhes adicionais em formato JSON
            user: Usuário responsável pelo evento

        Returns:
            ArticleEvent instance

        Example:
            ArticleEvent.create(
                article=article_instance,
                name="validation_completed",
                detail={"status": "success", "errors": []},
                user=request.user
            )
        """
        try:
            obj = cls()
            obj.article = article
            obj.name = name
            obj.detail = detail
            obj.creator = user
            obj.save()
            return obj
        except Exception as e:
            logging.exception(f"Error creating ArticleEvent: {e}")
            raise EventSaveError(f"Unable to create article event: {e}")


class ArticleExporter(BaseExporter):
    """
    Controla exportações de fascículos para o ArticleMeta
    """

    parent = ParentalKey(
        Article,
        on_delete=models.CASCADE,
        related_name="exporter",
        verbose_name=_("Article"),
    )
