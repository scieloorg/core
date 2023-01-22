import requests
import xmltodict
import json

from .models import ScieloJournal, Issue
from processing_errors.models import ProcessingError


def get_collection():
    try:
        collections_urls = requests.get("https://articlemeta.scielo.org/api/v1/collection/identifiers/",
                                        timeout=10)
        for collection in json.loads(collections_urls.text):
            yield collection.get('domain')

    except Exception as e:
        error = ProcessingError()
        error.step = "Collection url search error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def get_issn(collection):
    try:
        collections = requests.get(
            f"http://{collection}/scielo.php?script=sci_alphabetic&lng=es&nrm=iso&debug=xml", timeout=10)
        data = xmltodict.parse(collections.text)

        for issn in data['SERIALLIST']['LIST']['SERIAL']:
            try:
                yield issn['TITLE']['@ISSN']
            except Exception as e:
                error = ProcessingError()
                error.item = f"ISSN's list of {collection} collection error"
                error.step = "Get an ISSN from a collection error"
                error.description = str(e)[:509]
                error.type = str(type(e))
                error.save()

    except Exception as e:
        error = ProcessingError()
        error.step = "Collection ISSN's list search error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


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
                        number = item['@NUM']
                        year = str(item['@PUBDATE'])[:4]
                        month = str(item['@PUBDATE'])[4:6]
                        Issue.get_or_create(
                            journal=journal,
                            number=number,
                            volume=volume,
                            year=year,
                            month=month,
                            user=user
                        )
    except Exception as e:
        error = ProcessingError()
        error.item = f"Error getting or creating SciELO journal for {journal_xml['SERIAL']['ISSN_AS_ID']}"
        error.step = "SciELO journal record creation error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def load(user):
    for collection in get_collection():
        for issn in get_issn(collection):
            journal_xml = get_journal_xml(collection, issn)
            get_issue(user, journal_xml)
