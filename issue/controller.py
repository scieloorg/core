import json

import requests
import xmltodict

from processing_errors.models import ProcessingError

from .models import Issue, ScieloJournal


def get_journal_xml(collection, issn):
    try:
        journal = requests.get(
            f"http://{collection}/scielo.php?script=sci_issues&pid={issn}&lng=es&nrm=iso&debug=xml",
            timeout=10,
        )

        return xmltodict.parse(journal.text)

    except Exception as e:
        error = ProcessingError()
        error.item = f"Error getting the ISSN {issn} of the {collection} collection"
        error.step = "Journal record search error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def get_issue(user, journal_xml):
    issn_scielo = journal_xml["SERIAL"]["ISSN_AS_ID"]
    try:
        journal = ScieloJournal.objects.filter(issn_scielo=issn_scielo)[0]
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
                        journal=journal,
                        number=number,
                        volume=volume,
                        year=year,
                        month=month,
                        user=user,
                        supplement=supplement,
                    )
                except Exception as e:
                    error = ProcessingError()
                    error.item = f"Error getting or creating issue for {journal_xml['SERIAL']['ISSN_AS_ID']}"
                    error.step = "Issue record creating error"
                    error.description = str(e)[:509]
                    error.type = str(type(e))
                    error.save()

    except Exception as e:
        error = ProcessingError()
        error.item = (
            f"Error getting SciELO journal for {journal_xml['SERIAL']['ISSN_AS_ID']}"
        )
        error.step = "SciELO journal record recovery error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def load(user):
    for journal in ScieloJournal.objects.all().iterator():
        try:
            journal_xml = get_journal_xml(
                journal.collection.domain, journal.issn_scielo
            )
            get_issue(user, journal_xml)
        except Exception as e:
            error = ProcessingError()
            error.item = f"Error getting record XML"
            error.step = "SciELO journal record recovery error"
            error.description = str(e)[:509]
            error.type = str(type(e))
            error.save()
