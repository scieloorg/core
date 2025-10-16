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


def add_collections_to_pid_provider_items():
    for item in PidProviderXML.objects.filter(
        Q(issn_print__isnull=False) | Q(issn_electronic__isnull=False)
    ).exclude(collections__isnull=False):
        logging.info(item)
        add_collections_to_pid_provider(item)


def add_collections_to_pid_provider(pid_provider):
    """
    Obtém as coleções associadas ao PidProviderXML baseando-se nos ISSNs.

    Args:
        pid_provider: instância de PidProviderXML

    Returns:
        Lista de instâncias de Collection
    """
    # Coletar ISSNs
    try:
        issns = []
        if pid_provider.issn_electronic:
            issns.append(pid_provider.issn_electronic)
        if pid_provider.issn_print:
            issns.append(pid_provider.issn_print)

        if not issns:
            return []

        # Buscar coleções ativas através dos journals com esses ISSNs
        for item in SciELOJournal.objects.filter(
            Q(journal__official__issn_print__in=issns)
            | Q(journal__official__issn_electronic__in=issns),
        ).distinct():
            logging.info(item)
            pid_provider.collections.add(item.collection)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "add_collections_to_pid_provider",
                "pid_provider": str(pid_provider),
                "traceback": traceback.format_exc(),
            },
        )


def get_pp_xml_ids(
    collection_acron_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_updated_date=None,
    until_updated_date=None,
    proc_status_list=None,
):
    return select_pp_xml(
        collection_acron_list,
        journal_acron_list,
        from_pub_year,
        until_pub_year,
        from_updated_date,
        until_updated_date,
        proc_status_list=proc_status_list,
    ).values_list("id", flat=True)


def select_pp_xml(
    collection_acron_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_updated_date=None,
    until_updated_date=None,
    proc_status_list=None,
    params=None,
):
    params = params or {}

    q = Q()
    if journal_acron_list or collection_acron_list:
        issns = Journal.get_issn_list(collection_acron_list, journal_acron_list)
        issn_print_list = issns["issn_print_list"]
        issn_electronic_list = issns["issn_electronic_list"]

        if issn_print_list or issn_electronic_list:
            q = Q(issn_print__in=issn_print_list) | Q(
                issn_electronic__in=issn_electronic_list
            )
        elif issn_print_list:
            q = Q(issn_print__in=issn_print_list)
        elif issn_electronic_list:
            q = Q(issn_electronic__in=issn_electronic_list)

    if from_updated_date:
        params["updated__gte"] = from_updated_date
    if until_updated_date:
        params["updated__lte"] = until_updated_date

    if from_pub_year:
        params["pub_year__gte"] = from_pub_year
    if until_pub_year:
        params["pub_year__lte"] = until_pub_year

    if proc_status_list:
        params["proc_status__in"] = proc_status_list

    logging.info(params)
    return PidProviderXML.objects.filter(q, **params)


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
        if not article.is_available(collection_acron_list):
            raise ArticleIsNotAvailableError(
                f"Article {article} is not available. Unable to export to ArticleMeta."
            )
        events = []
        external_data = {
            "pid_v3": article.pid_v3,
            # "code": article.pid_v2,
            "created_at": article.created.strftime("%Y-%m-%d"),
            "document_type": article.article_type,
            "processing_date": article.updated.isoformat()[:10],
            "publication_date": article.pub_date,
            "publication_year": article.issue.year,
            "version": "xml",
        }
        events.append("building articlemeta format for article")
        article_data = am.build(article.xmltree, external_data)

        for legacy_keys in article.get_legacy_keys(
            collection_acron_list, is_active=True
        ):
            try:
                exporter = None
                response = None
                events = []
                data = {}
                col = legacy_keys.get("collection")
                pid = legacy_keys.get("pid")

                events.append("check articlemeta exportation demand")
                exporter = ArticleExporter.get_demand(
                    user, article, "articlemeta", pid, col, version, force_update
                )
                if not exporter:
                    # não encontrou necessidade de exportar
                    continue

                for avail_data in article.get_article_urls(collection=col, fmt="xml"):
                    events.append(avail_data)
                    if not (avail_data or {}).get("available"):
                        raise ArticleIsNotAvailableError(str(avail_data))
                    break

                data = {"collection": col.acron3}
                data.update(article_data)

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
    collection_acron_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=True,
    user=None,
    version=None,
) -> bool:
    """
    Bulk export articles to ArticleMeta.

    Args:
        collections (list): List of collection acronyms to filter articles.
        issn (str): ISSN to filter articles.
        number (int): Issue number to filter articles.
        volume (int): Issue volume to filter articles.
        year_of_publication (int): Year of publication to filter articles.
        from_date (str): Start date to filter articles.
        until_date (str): End date to filter articles.
        days_to_go_back (int): Number of days to go back from today or until_date to filter articles.
        force_update (bool): Whether to force update the export. Defaults to True.
        user (User): User object.
        client (MongoDB client): MongoDB client instance. A default client will be created if not provided.

    Returns:
        bool: True if the export was successful, False otherwise.
    """
    queryset = Article.select_items(
        collection_acron_list=collection_acron_list,
        journal_acron_list=journal_acron_list,
        from_pub_year=from_pub_year,
        until_pub_year=until_pub_year,
        from_updated_date=from_date,
        until_updated_date=until_date,
    )

    logging.info(f"Starting export of {queryset.count()} articles to ArticleMeta.")

    # Iterate over queryset and export each article to ArticleMeta
    for article in queryset.iterator():
        export_article_to_articlemeta(
            user,
            article=article,
            collection_acron_list=collection_acron_list,
            force_update=force_update,
            version=version,
        )


def fix_journal_articles(user, journal_id):
    try:
        journal = Journal.objects.get(id=journal_id)
        issns = journal.issns

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "load_journal_articles",
                "journal_id": journal_id,
                "articlemeta_export": articlemeta_export,
                "traceback": traceback.format_exc(),
            },
        )
    return


def load_journal_articles(user, journal_id, articlemeta_export=None):
    try:
        journal = Journal.objects.get(id=journal_id)
        issns = journal.issns

        for item in PidProviderXML.objects.filter(
            Q(issn_print__in=issns) | Q(issn_electronic__in=issns),
            proc_status__in=[PPXML_STATUS_TODO, PPXML_STATUS_DEDUPLICATED],
        ).iterator():
            load_article_from_pid_provider_xml(user, item, articlemeta_export)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "load_journal_articles",
                "journal_id": journal_id,
                "articlemeta_export": articlemeta_export,
                "traceback": traceback.format_exc(),
            },
        )
    return


def load_article_from_pid_provider_xml(user, pp_xml, articlemeta_export=None):
    try:
        # Carrega o artigo do arquivo XML
        logging.info(f"Loading article from PidProviderXML {pp_xml.id}")
        article = load_article(
            user,
            file_path=pp_xml.current_version.file.path,
            v3=pp_xml.v3,
            pp_xml=pp_xml,
        )
        # for item in article.legacy_article.select_related('collection').all():
        #     pp_xml.collections.add(item.collection)

        # article.check_availability(user)

        # for item in Article.objects.filter(sps_pkg_name=article.sps_pkg_name).exclude(id=article.id).iterator():
        #     item.data_status = DATA_STATUS_DUPLICATED
        #     item.save()

        # Exporta para ArticleMeta se solicitado
        if articlemeta_export and article.is_available():
            collection_acron_list = articlemeta_export.get("collection_acron_list")
            force_update = articlemeta_export.get("force_update", False)
            version = articlemeta_export.get("version")
            export_article_to_articlemeta(
                user,
                article,
                collection_acron_list,
                force_update,
                version=version,
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "load_article_from_pid_provider_xml",
                "pp_xml": str(pp_xml),
                "articlemeta_export": articlemeta_export,
                "traceback": traceback.format_exc(),
            },
        )
