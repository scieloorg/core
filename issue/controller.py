import requests
import xmltodict
import json

from .models import ScieloJournal, Issue
from processing_errors.models import ProcessingError


def get_journal_xml(collection, issn):
    try:
        journal = requests.get(
            f"http://{collection}/scielo.php?script=sci_issues&pid={issn}&lng=es&nrm=iso&debug=xml", timeout=10
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
    issn_scielo = journal_xml['SERIAL']['ISSN_AS_ID']
    try:
        journal = ScieloJournal.objects.filter(issn_scielo=issn_scielo)[0]
        for issue in journal_xml['SERIAL']['AVAILISSUES']['YEARISSUE']:
                volume = issue['VOLISSUE']['@VOL']
                for item in issue['VOLISSUE']['ISSUE']:
                    try:
                        number = item['@NUM']
                        year = str(item['@PUBDATE'])[:4]
                        month = str(item['@PUBDATE'])[4:6]
                        # value not available in XML file
                        supp = None
                        Issue.get_or_create(
                            journal=journal,
                            number=number,
                            volume=volume,
                            year=year,
                            month=month,
                            user=user,
                            supp=supp,
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
        error.item = f"Error getting SciELO journal for {journal_xml['SERIAL']['ISSN_AS_ID']}"
        error.step = "SciELO journal record recovery error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def load(user):
    for journal in ScieloJournal.objects.all().iterator():
        journal_xml = get_journal_xml(journal.collection.domain, journal.issn_scielo)
        get_issue(user, journal_xml)
