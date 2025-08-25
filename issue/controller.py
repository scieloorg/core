from datetime import datetime

import json
import logging
import sys

import requests
import xmltodict

from django.db.models import Q

from core.utils.date_utils import get_date_range
from core.mongodb import write_to_db
from journal.models import SciELOJournal
from tracker.models import UnexpectedEvent

from .models import Issue, IssueExport


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
    issue_code, # FIXME: Use a different identifier instead of pk
    force_update=True, 
    user=None,
    client=None,
):
    try:
        issue = Issue.objects.get(pk=issue_code)
    except Issue.DoesNotExist:
        logging.error(f"Issue with id {issue_code} does not exist.")
        return False

    if not issue.journal:
        logging.error(f"Issue {issue_code} does not have a valid journal.")
        return False

    for scielo_journal in issue.journal.scielojournal_set.all():
        if not force_update and IssueExport.is_exported(issue, 'articlemeta', scielo_journal.collection):
            logging.info(f"Issue {issue_code} already exported to collection {scielo_journal.collection}. Skipping.")
            continue
        try:
            issue_data = issue.articlemeta_format(scielo_journal.collection.acron3)
            issue_data['processing_date'] = datetime.strptime(issue_data['processing_date'], "%Y-%m-%d")
        except Exception as e:
            logging.error(f"Error converting issue data for ArticleMeta export for issue {issue_code}: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "export_issue_to_articlemeta",
                    "issue_code": issue_code,
                    "collection": scielo_journal.collection,
                    "force_update": force_update,
                }
            )

        try:
            write_to_db(
                issue_data, 
                "articlemeta", 
                "issues", 
                force_update=force_update,
                client=client,
            )
            IssueExport.mark_as_exported(issue, 'articlemeta', scielo_journal.collection, user)
        except Exception as e:
            logging.error(f"Error exporting issue {issue_code} to ArticleMeta: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "export_issue_to_articlemeta",
                    "issue_code": issue_code,
                    "collection": scielo_journal.collection,
                    "force_update": force_update,
                }
            )

    return True
    

def bulk_export_issues_to_articlemeta(
    collections=[],
    issn=None,
    volume=None,
    number=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=True, 
    user=None,
    client=None,
):
    """
    Export issues to ArticleMeta.

    Args:
        collections (list): List of collections to export.
        issn (str): ISSN of the journal to export.
        volume (str): Volume of the issue to export.
        number (str): Number of the issue to export.
        from_date (str): Start date of the range to export.
        until_date (str): End date of the range to export.
        days_to_go_back (int): Number of days to go back from today to get the start date.
        force_update (bool): Whether to force update existing records.
        user (User): User object.
        client (Client): Client object.
    """
    filters = {}
    
    # Collections filter
    if collections:
        filters['journal__scielojournal__collection__acron3__in'] = collections

    # Volume filter
    if volume:
        filters['volume'] = volume

    # Number filter
    if number:
        filters['number'] = number

    # Date range filters
    if from_date or until_date or days_to_go_back:
        from_date_str, until_date_str = get_date_range(from_date, until_date, days_to_go_back)
        filters['updated__range'] = (from_date_str, until_date_str)

    # Build queryset with filters
    queryset = Issue.objects.filter(**filters)

    # Add ISSN filter separately using Q objects
    if issn:
        queryset = queryset.filter(
            Q(journal__official__issn_print=issn) | 
            Q(journal__official__issn_electronic=issn)
        )
        
    logging.info(f"Starting export of {queryset.count()} issues to ArticleMeta.")
    
    for issue in queryset.iterator():
        export_issue_to_articlemeta(
            issue_code=issue.pk,
            force_update=force_update,
            user=user,
            client=client,
        )

    logging.info("Export completed.")
