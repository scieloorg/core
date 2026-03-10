import csv
import json
import logging
import sys
import traceback
from datetime import datetime

from django.db.models import Q
from packtools.sps.formats.am import am

from article.sources.xmlsps import load_article
from article.models import Article, ArticleExporter, ArticleFunding
from article.choices import (
    DATA_STATUS_DUPLICATED,
    DATA_STATUS_DEDUPLICATED,
    DATA_STATUS_PUBLIC,
)
from core.mongodb import write_item
from core.utils import date_utils
from doi_manager.models import CrossRefConfiguration
from institution.models import Sponsor
from journal.models import Journal, SciELOJournal
from pid_provider.choices import (
    PPXML_STATUS_TODO,
    PPXML_STATUS_DUPLICATED,
    PPXML_STATUS_DEDUPLICATED,
    PPXML_STATUS_INVALID,
)
from pid_provider.models import PidProviderXML, XMLVersionXmlWithPreError
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


def build_crossmark_data(article, collection):
    """
    Builds the crossmark data structure for a given article and collection,
    ready to be written to the ``crossmark_article`` MongoDB collection.

    The document contains:
    - ``code``: article PID (v2)
    - ``collection``: collection acronym
    - ``doi``: article DOI value (first available)
    - ``crossmark_policy``: CrossMark policy URL from CrossRef configuration
    - ``updates``: list of Crossref update entries derived from the article's
      related articles that have a ``crossref_update_type`` set

    Args:
        article: Article instance
        collection: Collection instance with ``acron3`` attribute

    Returns:
        dict: crossmark data document, or ``None`` if there are no updates to export
    """
    # Resolve article DOI
    doi_value = None
    doi_obj = article.doi.first()
    if doi_obj:
        doi_value = doi_obj.value

    # Resolve CrossMark policy URL via the journal DOI prefix.
    # DOIs follow the format "prefix/suffix" where the prefix is the registrant
    # identifier (e.g. "10.1590").
    crossmark_policy = None
    if doi_value:
        prefix = doi_value.split("/")[0] if "/" in doi_value else None
        if prefix:
            crossmark_policy = CrossRefConfiguration.get_crossmark_policy(prefix)

    # Build update list from related articles that carry a crossref_update_type
    updates = []
    for related in article.related_articles.filter(
        crossref_update_type__isnull=False
    ).select_related("related_article"):
        update_entry = {
            "update_type": related.crossref_update_type,
            "doi": related.href,
        }
        # Attach publication date from the related article when available
        if related.related_article:
            ra = related.related_article
            if ra.pub_date_year:
                date_entry = {"year": ra.pub_date_year}
                if ra.pub_date_month:
                    date_entry["month"] = ra.pub_date_month
                update_entry["date"] = date_entry
        updates.append(update_entry)

    if not updates:
        return None

    return {
        "code": article.pid_v2,
        "collection": collection.acron3,
        "doi": doi_value,
        "crossmark_policy": crossmark_policy,
        "updates": updates,
    }


def export_crossmark_article_to_articlemeta(
    user,
    article,
    collection_acron_list=None,
):
    """
    Exports crossmark data for the given article to the ``crossmark_article``
    MongoDB collection.

    A separate document per (code, collection) pair is upserted so that
    crossmark data does not interfere with the main ``articles`` collection.

    Args:
        user: User object
        article: Article instance
        collection_acron_list: Optional list of collection acronyms to restrict
            the export

    Returns:
        None
    """
    try:
        legacy_keys_items = list(
            article.get_legacy_keys(collection_acron_list, is_active=True)
        )
        if not legacy_keys_items:
            return

        for legacy_keys in legacy_keys_items:
            try:
                col = legacy_keys.get("collection")
                if col is None:
                    continue

                data = build_crossmark_data(article, col)
                if not data:
                    continue

                write_item("crossmark_article", data)

            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "operation": "export_crossmark_article_to_articlemeta",
                        "article": str(article),
                        "legacy_keys": str(legacy_keys),
                        "traceback": traceback.format_exc(),
                    },
                )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "export_crossmark_article_to_articlemeta",
                "article": str(article),
                "collection_acron_list": collection_acron_list,
                "traceback": traceback.format_exc(),
            },
        )
