import json
import logging
import sys
import traceback
from datetime import datetime

import requests
import xmltodict
from django.db.models import Q

from core.mongodb import write_item
from issue.models import Issue, IssueExporter
from journal.models import SciELOJournal
from tracker.models import UnexpectedEvent


def get_journal_xml(collection, issn):
    try:
        journal = requests.get(
            f"http://{collection}/scielo.php?script=sci_issues&pid={issn}&lng=es&nrm=iso&debug=xml",
            timeout=10,
        )

        return xmltodict.parse(journal.text)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="issue.controller.get_journal_xml",
                message=f"Error getting the ISSN {issn} of the {collection} collection",
            ),
        )


def get_issue(user, journal_xml, collection):
    issn_scielo = journal_xml["SERIAL"]["ISSN_AS_ID"]

    if not issn_scielo:
        logging.info(f"No ISSN found for journal")
        pass

    try:
        scielo_journal = SciELOJournal.get(
            collection=collection, issn_scielo=issn_scielo
        )
        for issue in journal_xml["SERIAL"]["AVAILISSUES"]["YEARISSUE"]:
            try:
                volume = issue["VOLISSUE"]["@VOL"]
            except KeyError:
                volume = None
            for item in issue["VOLISSUE"]["ISSUE"]:
                try:
                    number = item["@NUM"]
                except KeyError:
                    number = None
                try:
                    year = str(item["@PUBDATE"])[:4]
                    month = str(item["@PUBDATE"])[4:6]
                except KeyError:
                    year = None
                    month = None
                # value not available in XML file
                supplement = None
                try:
                    Issue.get_or_create(
                        journal=scielo_journal.journal,
                        number=number,
                        volume=volume,
                        year=year,
                        month=month,
                        user=user,
                        supplement=supplement,
                        markup_done=False,
                        season=None,
                    )
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail=dict(
                            function="issue.controller.get_issue",
                            message=f"Error getting or creating issue for {journal_xml['SERIAL']['ISSN_AS_ID']}",
                        ),
                    )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="issue.controller.get_issue",
                message=f"Error getting SciELO journal for {journal_xml['SERIAL']['ISSN_AS_ID']}",
            ),
        )


def load(user):
    for journal in SciELOJournal.objects.all().iterator():
        try:
            journal_xml = get_journal_xml(
                journal.collection.domain, journal.issn_scielo
            )
            get_issue(user, journal_xml, journal.collection)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    function="issue.controller.load",
                    message=f"Error getting record XML",
                ),
            )


def export_issue_to_articlemeta(
    user,
    issue,
    collection_acron_list=None,
    force_update=None,
    version=None,
):
    try:
        events = None
        if not issue:
            raise ValueError("export_issue_to_articlemeta requires issue")
        for legacy_keys in issue.get_legacy_keys(collection_acron_list, is_active=True):
            try:
                exporter = None
                response = None
                events = []
                col = legacy_keys.get("collection")
                pid = legacy_keys.get("pid")
                logging.info(
                    (user, issue, "articlemeta", pid, col, version, force_update)
                )
                events.append("check articlemeta exportation demand")
                exporter = IssueExporter.get_demand(
                    user, issue, "articlemeta", pid, col, version, force_update
                )
                if not exporter:
                    # não encontrou necessidade de exportar
                    continue

                events.append("building articlemeta format for issue")
                issue_data = issue.articlemeta_format(col.acron3)

                try:
                    json.dumps(issue_data)
                except Exception as e:
                    logging.exception(e)
                    response = str(issue_data)
                    raise e

                events.append("writing issue to articlemeta database")
                response = write_item("issues", issue_data)
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
                        response=response,
                        errors=None,
                        exceptions=traceback.format_exc(),
                    )
                else:
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "operation": "export_article_to_articlemeta",
                            "issue": str(issue),
                            "collection": str(col),
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
                "operation": "export_issue_to_articlemeta",
                "issue": issue,
                "collection_acron_list": collection_acron_list,
                "force_update": force_update,
                "events": events,
            },
        )


def bulk_export_issues_to_articlemeta(
    user=None,
    collection_acron_list=None,
    journal_acron_list=None,
    publication_year=None,
    volume=None,
    number=None,
    supplement=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=None,
    version=None,
):
    """
    Export issues to ArticleMeta Database with flexible filtering.

    Args:
        user: User object for authentication
        collection_acron_list: List of collections acronyms (e.g., ["scl", "mex"])
        journal_acron_list: List of journal acronyms to filter
        publication_year: Filter by publication year
        volume: Filter by volume number
        number: Filter by issue number
        supplement: Filter by supplement
        from_date: Export issues modified from this date
        until_date: Export issues modified until this date
        days_to_go_back: Export issues modified from this number of days ago
        force_update: Force update existing records
        version: Version identifier for export
    """
    try:
        queryset = Issue.select_issues(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            publication_year=publication_year,
            volume=volume,
            number=number,
            supplement=supplement,
            from_date=from_date,
            until_date=until_date,
            days_to_go_back=days_to_go_back,
        )

        for issue in queryset.iterator():
            try:
                export_issue_to_articlemeta(
                    user,
                    issue=issue,
                    collection_acron_list=collection_acron_list,
                    force_update=force_update,
                    version=version,
                )
            except Exception as e:
                # Registra erro do issue mas continua processando outros
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "function": "bulk_export_issues_to_articlemeta",
                        "issue_id": issue.id,
                        "journal_acron": getattr(issue, "journal_acron", None),
                        "publication_year": getattr(issue, "publication_year", None),
                        "volume": getattr(issue, "volume", None),
                        "number": getattr(issue, "number", None),
                        "supplement": getattr(issue, "supplement", None),
                        "force_update": force_update,
                    },
                )
                continue
                
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "bulk_export_issues_to_articlemeta",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "publication_year": publication_year,
                "volume": volume,
                "number": number,
                "supplement": supplement,
                "from_date": str(from_date) if from_date else None,
                "until_date": str(until_date) if until_date else None,
                "days_to_go_back": days_to_go_back,
                "force_update": force_update,
            },
        )
        raise