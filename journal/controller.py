import requests
import xmltodict
import json

from .models import OfficialJournal, ScieloJournal, ScieloJournalTitle, Mission
from institution.models import Institution
from processing_errors.models import ProcessingError


def get_collection():
    try:
        collections_urls = requests.get("https://articlemeta.scielo.org/api/v1/collection/identifiers/", timeout=10)
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
        collections = requests.get(f"http://{collection}/scielo.php?script=sci_alphabetic&lng=es&nrm=iso&debug=xml",
                                   timeout=10)
        data = xmltodict.parse(collections.text)

        for issn in data['SERIALLIST']['LIST']['SERIAL']:
            yield issn['TITLE']['@ISSN']

    except Exception as e:
        error = ProcessingError()
        error.step = "Collection ISSN's list search error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def get_journal_xml(collection, issn):
    try:
        official_journal = requests.get(
            f"http://{collection}/scielo.php?script=sci_serial&pid={issn}&lng=es&nrm=iso&debug=xml", timeout=10)
        journal_xml = xmltodict.parse(official_journal.text)
        return journal_xml

    except Exception as e:
        error = ProcessingError()
        error.step = "Journal record search error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def get_official_journal(user, journal_xml):
    try:
        issnl = journal_xml['SERIAL']['ISSN_AS_ID']
        title = journal_xml['SERIAL']['TITLEGROUP']['TITLE']
        # this value are not available in the XML file
        foundation_year = ''
        issns = journal_xml['SERIAL']['TITLE_ISSN']
        issns_list = issns if type(issns) is list else [issns]
        issn_print = ''
        issn_electronic = ''

        for issn in issns_list:
            if issn['@TYPE'] == 'PRINT':
                issn_print = issn['#text']
            if issn['@TYPE'] == 'ONLIN':
                issn_electronic = issn['#text']

        official_journal = OfficialJournal().get_or_create(title, foundation_year, issn_print,
                                                           issn_electronic, issnl, user)

        return official_journal

    except Exception as e:
        error = ProcessingError()
        error.step = "Official journal record creation error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


