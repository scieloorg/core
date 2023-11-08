import json
import sys

import requests
import xmltodict

from tracker.models import UnexpectedEvent

from .models import Issue
from journal.models import SciELOJournal


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
            e=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="issue.controller.get_journal_xml",
                message=f"Error getting the ISSN {issn} of the {collection} collection"
            )
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
                        e=e,
                        exc_traceback=exc_traceback,
                        detail=dict(
                            function="issue.controller.get_issue",
                            message=f"Error getting or creating issue for {journal_xml['SERIAL']['ISSN_AS_ID']}"
                        )
                    )                    


    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            e=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="issue.controller.get_issue",
                message=f"Error getting SciELO journal for {journal_xml['SERIAL']['ISSN_AS_ID']}"
            )
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
                e=e,
                exc_traceback=exc_traceback,
                detail=dict(
                    function="issue.controller.load",
                    message=f"Error getting record XML"
                )
            )
