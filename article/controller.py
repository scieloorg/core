import csv
import itertools
import json
import logging
import sys
import traceback

from packtools.sps.formats.am import am

from article.models import Article, ArticleExporter, ArticleFunding, ArticleSource
from article import choices
from collection.models import Collection
from core.mongodb import write_item
from core.utils.harvesters import AMHarvester, OPACHarvester
from institution.models import Sponsor
from journal.models import Journal
from pid_provider.choices import (
    PPXML_STATUS_TODO,
    PPXML_STATUS_INVALID,
)
from pid_provider.models import PidProviderXML
from tracker.models import UnexpectedEvent


class ArticleIsNotAvailableError(Exception): ...


# def get_pp_xml_ids(
#     collection_acron_list=None,
#     journal_acron_list=None,
#     from_pub_year=None,
#     until_pub_year=None,
#     from_updated_date=None,
#     until_updated_date=None,
#     proc_status_list=None,
# ):
#     return select_pp_xml(
#         collection_acron_list,
#         journal_acron_list,
#         from_pub_year,
#         until_pub_year,
#         from_updated_date,
#         until_updated_date,
#         proc_status_list=proc_status_list,
#     ).values_list("id", flat=True)


# def select_pp_xml(
#     collection_acron_list=None,
#     journal_acron_list=None,
#     from_pub_year=None,
#     until_pub_year=None,
#     from_updated_date=None,
#     until_updated_date=None,
#     proc_status_list=None,
#     params=None,
# ):
#     params = params or {}

#     q = Q()
#     if journal_acron_list or collection_acron_list:
#         issns = Journal.get_issn_list(collection_acron_list, journal_acron_list)
#         issn_print_list = issns["issn_print_list"]
#         issn_electronic_list = issns["issn_electronic_list"]

#         if issn_print_list or issn_electronic_list:
#             q = Q(issn_print__in=issn_print_list) | Q(
#                 issn_electronic__in=issn_electronic_list
#             )
#         elif issn_print_list:
#             q = Q(issn_print__in=issn_print_list)
#         elif issn_electronic_list:
#             q = Q(issn_electronic__in=issn_electronic_list)

#     if from_updated_date:
#         params["updated__gte"] = from_updated_date
#     if until_updated_date:
#         params["updated__lte"] = until_updated_date

#     if from_pub_year:
#         params["pub_year__gte"] = from_pub_year
#     if until_pub_year:
#         params["pub_year__lte"] = until_pub_year

#     if proc_status_list:
#         params["proc_status__in"] = proc_status_list

#     logging.info(params)
#     return PidProviderXML.objects.filter(q, **params)


def load_financial_data(row, user):
    article_findings = []
    for institution in row.get("funding_source").split(","):
        sponsor = Sponsor.get_or_create(
            user=user,
            name=institution,
            acronym=None,
            level_1=None,
            level_2=None,
            level_3=None,
            location=None,
            official=None,
            is_official=None,
            url=None,
            institution_type=None,
        )
        article_findings.append(
            ArticleFunding.get_or_create(
                award_id=row.get("award_id"), funding_source=sponsor, user=user
            )
        )
    article = Article.get_or_create(
        pid_v2=row.get("pid_v2"), fundings=article_findings, user=user
    )

    return article


def read_file(user, file_path):
    with open(file_path, "r") as csvfile:
        data = csv.DictReader(csvfile)
        for row in data:
            logging.debug(row)
            load_financial_data(row, user)


def export_article_to_articlemeta(
    user,
    article,
    collection_acron_list=None,
    force_update=None,
    version=None,
) -> bool:

    try:
        if not article.classic_available(collection_acron_list):
            raise ArticleIsNotAvailableError(
                f"Article {article} {collection_acron_list} (classic) is not available. Unable to export to ArticleMeta."
            )
        new_available = article.new_available(collection_acron_list).exists()
        logging.info(f"Article new {article} {collection_acron_list} {new_available}")

        logging.info(
            f"export_article_to_articlemeta: {article}, collections: {collection_acron_list}, force_update: {force_update}"
        )
        legacy_keys_items = list(article.get_legacy_keys(
            collection_acron_list, is_active=True
        ))
        logging.info(f"Legacy keys to process: {legacy_keys_items}")
        if not legacy_keys_items:
            UnexpectedEvent.create(
                exception=ValueError("No legacy keys found for article"),
                detail={
                    "operation": "export_article_to_articlemeta",
                    "article": str(article),
                    "collection_acron_list": collection_acron_list,
                    "force_update": force_update,
                },
            )
            return

        events = []
        external_data = {
            "created_at": article.created.strftime("%Y-%m-%d"),
            "document_type": article.article_type,
            "processing_date": article.updated.strftime("%Y-%m-%d"),
            "publication_date": article.pub_date,
            "publication_year": article.issue.year,
            "version": "xml",
        }
        if new_available:
            external_data["pid_v3"] = article.pid_v3

        text_langs = article.get_text_langs()
        
        article_data = {}
        for legacy_keys in legacy_keys_items:
            try:
                exporter = None
                response = None
                events = []
                data = {}
                col = legacy_keys.get("collection")
                pid = legacy_keys.get("pid")

                if not article_data:
                    events.append("building articlemeta format for article")
                    article_data = am.build(article.xmltree, external_data)

                events.append("check articlemeta exportation demand")
                exporter = ArticleExporter.get_demand(
                    user, article, "articlemeta", pid, col, version, force_update
                )
                if not exporter:
                    # não encontrou necessidade de exportar
                    continue

                data = {"collection": col.acron3}
                data.update(article_data)
                data["article"]["fulltext_langs"] = text_langs.get(col.acron3, {})

                events.append("building articlemeta format for issue")
                issue_data = article.issue.articlemeta_format(col.acron3)
                data.update(issue_data)

                events.append("updating articlemeta format with issue data")
                # Issue data
                data["code_issue"] = issue_data["code"]
                data["issue"] = issue_data["issue"]

                # Journal data
                events.append("updating articlemeta format with journal data")
                data["code_title"] = [
                    x for x in issue_data["code_title"] if x is not None
                ]
                data["title"] = issue_data["title"]
                data["code"] = pid or article.pid_v2
                data.update(external_data)

                if not data["article"]:
                    raise ValueError("Missing 'article' in data")

                try:
                    json.dumps(data)
                    data["code"]
                except Exception as e:
                    logging.exception(e)
                    response = str(data)
                    logging.info(data)
                    raise e

                # Export the article to ArticleMeta
                events.append("writing article to articlemeta database")
                response = write_item("articles", data)

                # Mark the article as exported to ArticleMeta in the collection
                exporter.finish(
                    user,
                    completed=True,
                    events=events,
                    response=response,
                    errors=None,
                    exceptions=None,
                )

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if exporter:
                    exporter.finish(
                        user,
                        completed=False,
                        events=events,
                        response=response or str(data),
                        errors=None,
                        exceptions=traceback.format_exc(),
                    )
                else:
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "operation": "export_article_to_articlemeta",
                            "article": str(article),
                            "legacy_keys": str(legacy_keys),
                            "events": events,
                            "traceback": traceback.format_exc(),
                        },
                    )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "export_article_to_articlemeta",
                "article": str(article),
                "collection_acron_list": collection_acron_list,
                "force_update": force_update,
                "traceback": traceback.format_exc(),
            },
        )


def bulk_export_articles_to_articlemeta(
    user,
    collection_acron_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=None,
    version=None,
):
    """
    Bulk export articles to ArticleMeta.

    Args:
        user: User object
        collection_acron_list: List of collection acronyms to filter articles
        journal_acron_list: List of journal acronyms to filter articles
        from_pub_year: Start publication year to filter articles
        until_pub_year: End publication year to filter articles
        from_date: Start date to filter articles
        until_date: End date to filter articles
        days_to_go_back: Number of days to go back from today or until_date
        force_update: Whether to force update the export. Defaults to True
        version: Version identifier for export

    Returns:
        bool: True if the export was successful, False otherwise
    """
    try:
        params = {}
        if not force_update:
            # seleciona os artigos considerados publicados
            params = {
                "is_classic_public": True,
            }
        queryset = Article.select_items(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_pub_year=from_pub_year,
            until_pub_year=until_pub_year,
            from_updated_date=from_date,
            until_updated_date=until_date,
            params=params
        )
        if not queryset.exists():
            UnexpectedEvent.create(
                exception=ValueError("No articles found for the given filters"),
                detail={
                    "operation": "bulk_export_articles_to_articlemeta",
                    "collection_acron_list": collection_acron_list,
                    "journal_acron_list": journal_acron_list,
                    "from_pub_year": from_pub_year,
                    "until_pub_year": until_pub_year,
                    "from_date": str(from_date) if from_date else None,
                    "until_date": str(until_date) if until_date else None,
                    "days_to_go_back": days_to_go_back,
                    "force_update": force_update,
                },
            )
            return False

        for article in queryset.iterator():
            try:
                if force_update:
                    article.check_availability(user)
                if not article.is_classic_public:
                    continue
                export_article_to_articlemeta(
                    user,
                    article=article,
                    collection_acron_list=collection_acron_list,
                    force_update=force_update,
                    version=version,
                )
            except Exception as e:
                # Registra erro do article mas continua processando outros
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "function": "bulk_export_articles_to_articlemeta",
                        "article_id": article.id,
                        "article_pid": getattr(article, "pid", None),
                        "journal_acron": getattr(article, "journal_acron", None),
                        "pub_year": getattr(article, "pub_year", None),
                        "force_update": force_update,
                    },
                )
                continue
        
        return True
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "bulk_export_articles_to_articlemeta",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_date": str(from_date) if from_date else None,
                "until_date": str(until_date) if until_date else None,
                "days_to_go_back": days_to_go_back,
                "force_update": force_update,
            },
        )
        raise


class ArticleIteratorBuilder:
    """
    Monta e encadeia iteradores de seleção de artigos para despacho ao pipeline.

    Cada método ``_iter_from_*`` é um gerador que yields kwargs prontos para
    ``task_process_article_pipeline``. Os iteradores ativos são determinados
    pelos argumentos exclusivos presentes na instância — múltiplos podem estar
    ativos simultaneamente.

    Argumentos exclusivos e seus iteradores:

    ========================= ================================================
    Argumento exclusivo        Iterador ativado
    ========================= ================================================
    proc_status_list           _iter_from_pid_provider
    data_status_list           _iter_from_article
    limit / timeout / opac_url _iter_from_harvest
    article_source_status_list _iter_from_article_source
    (nenhum)                   _iter_from_pid_provider (padrão)
    ========================= ================================================

    Usage::

        it = ArticleIteratorBuilder(
            user=user,
            collection_acron_list=["scl"],
            proc_status_list=["todo"],
            data_status_list=["invalid"],
        )
        for kwargs in it:
            task_process_article_pipeline.delay(**kwargs)
    """

    def __init__(
        self,
        user,
        collection_acron_list=None,
        journal_acron_list=None,
        from_pub_year=None,
        until_pub_year=None,
        from_date=None,
        until_date=None,
        proc_status_list=None,
        data_status_list=None,
        article_source_status_list=None,
        limit=None,
        timeout=None,
        opac_url=None,
        force_update=None,
    ):
        self.user = user
        self.collection_acron_list = collection_acron_list
        self.journal_acron_list = journal_acron_list
        self.from_pub_year = from_pub_year
        self.until_pub_year = until_pub_year
        self.from_date = from_date
        self.until_date = until_date
        self.proc_status_list = proc_status_list
        self.data_status_list = data_status_list
        self.article_source_status_list = article_source_status_list
        self.limit = limit
        self.timeout = timeout
        self.opac_url = opac_url
        self.force_update = force_update

    def __iter__(self):
        yield from self._iter_from_harvest()
        yield from self._iter_from_article_source()
        yield from self._iter_from_pid_provider()
        yield from self._iter_from_article()

    # ------------------------------------------------------------------
    # Iteradores de seleção
    # ------------------------------------------------------------------

    def _iter_from_pid_provider(self):
        """Itera PidProviderXML filtrados por periódico, data e status."""
        journal_issn_groups = (
            Journal.get_journal_issns(self.collection_acron_list, self.journal_acron_list)
            or [None]
        )
        for journal_issns in journal_issn_groups:
            issn_list = [i for i in journal_issns if i] if journal_issns else None
            if journal_issns and not issn_list:
                continue
            qs = PidProviderXML.get_queryset(
                issn_list=issn_list,
                from_pub_year=self.from_pub_year,
                until_pub_year=self.until_pub_year,
                from_updated_date=self.from_date,
                until_updated_date=self.until_date,
                proc_status_list=self.proc_status_list or [PPXML_STATUS_TODO, PPXML_STATUS_INVALID],
            )
            for item in qs.iterator():
                yield {"pp_xml_id": item.id}

    def _iter_from_article(self):
        """
        Itera Articles filtrados por data_status.
        Yields None para artigos sem pp_xml recuperável (sinaliza skip).
        """
        filters = {
            "data_status__in": self.data_status_list or [
                choices.DATA_STATUS_PENDING,
                choices.DATA_STATUS_UNDEF,
                choices.DATA_STATUS_INVALID,
            ]
        }
        journal_id_list = Journal.get_ids(
            collection_acron_list=self.collection_acron_list,
            journal_acron_list=self.journal_acron_list,
        )
        if journal_id_list:
            filters["journal__in"] = journal_id_list
        if self.from_pub_year:
            filters["pub_year__gte"] = self.from_pub_year
        if self.until_pub_year:
            filters["pub_year__lte"] = self.until_pub_year
        if self.from_date:
            filters["updated__gte"] = self.from_date
        if self.until_date:
            filters["updated__lte"] = self.until_date

        for article in Article.objects.filter(**filters).iterator():
            if not article.pp_xml:
                try:
                    article.pp_xml = PidProviderXML.get_by_pid_v3(pid_v3=article.pid_v3)
                    article.save(update_fields=["pp_xml"])
                except Exception as e:
                    logging.error(f"pp_xml not found for article {article.id}: {e}")
                    yield None
                    continue
            yield {"pp_xml_id": article.pp_xml.id}

    def _iter_from_harvest(self):
        """Itera documentos coletados via OPAC ou ArticleMeta."""
        if Collection.objects.count() == 0:
            Collection.load(self.user)

        for collection_acron in self.collection_acron_list or list(Collection.get_acronyms()):
            harvester = self._build_harvester(collection_acron)
            for document in harvester.harvest_documents():
                yield {
                    "xml_url": document["url"],
                    "collection_acron": collection_acron,
                    "pid": document["pid_v2"],
                    "source_date": document.get("processing_date") or document.get("origin_date"),
                }

    def _iter_from_article_source(self):
        """Itera ArticleSources pendentes ou com erro."""
        for article_source in ArticleSource.get_queryset_to_complete_data(
            self.from_date,
            self.until_date,
            self.force_update,
            self.article_source_status_list,
        ):
            yield {"article_source_id": article_source.id}

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _build_harvester(self, collection_acron):
        """Instancia o harvester adequado para a coleção."""
        kwargs = dict(
            from_date=self.from_date,
            until_date=self.until_date,
            limit=self.limit,
            timeout=self.timeout,
        )
        if collection_acron == "scl":
            return OPACHarvester(self.opac_url or "www.scielo.br", collection_acron, **kwargs)
        return AMHarvester("article", collection_acron, **kwargs)

