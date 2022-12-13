import requests
import xmltodict
import json

from .models import OfficialJournal, ScieloJournal, ScieloJournalTitle, Mission, JournalLoadError
from institution.models import Institution, InstitutionHistory


def get_collection():
    try:
        collections_urls = requests.get("https://articlemeta.scielo.org/api/v1/collection/identifiers/", timeout=10)
        for collection in json.loads(collections_urls.text):
            yield collection.get('domain')

    except Exception as e:
        error = JournalLoadError()
        error.step = "Collection url search error"
        error.description = str(e)[:509]
        error.save()


def get_issn(collection):
    try:
        collections = requests.get(f"http://{collection}/scielo.php?script=sci_alphabetic&lng=es&nrm=iso&debug=xml",
                                   timeout=10)
        data = xmltodict.parse(collections.text)

        for issn in data['SERIALLIST']['LIST']['SERIAL']:
            yield issn['TITLE']['@ISSN']

    except Exception as e:
        error = JournalLoadError()
        error.step = "Collection ISSN's list search error"
        error.description = str(e)[:509]
        error.save()


def get_journal_xml(collection, issn):
    try:
        official_journal = requests.get(
            f"http://{collection}/scielo.php?script=sci_serial&pid={issn}&lng=es&nrm=iso&debug=xml", timeout=10)
        journal_xml = xmltodict.parse(official_journal.text)
        return journal_xml

    except Exception as e:
        error = JournalLoadError()
        error.step = "Journal record search error"
        error.description = str(e)[:509]
        error.save()


def get_official_journal(user, journal_xml):
    try:
        issnl = journal_xml['SERIAL']['ISSN_AS_ID']
        official_journals = OfficialJournal.objects.filter(ISSNL=issnl)
        try:
            official_journal = official_journals[0]
        except IndexError:
            official_journal = OfficialJournal()
            official_journal.ISSNL = issnl
            official_journal.title = journal_xml['SERIAL']['TITLEGROUP']['TITLE']
            issns = journal_xml['SERIAL']['TITLE_ISSN']
            if type(issns) is list:
                for issn in issns:
                    if issn['@TYPE'] == 'PRINT':
                        official_journal.ISSN_print = issn['#text']
                    if issn['@TYPE'] == 'ONLIN':
                        official_journal.ISSN_electronic = issn['#text']
            else:
                if issns['@TYPE'] == 'PRINT':
                    official_journal.ISSN_print = issns['#text']
                if issns['@TYPE'] == 'ONLIN':
                    official_journal.ISSN_electronic = issns['#text']
            foundation_year = journal_xml['SERIAL']['journal-status-history']['periods']['date-status']
            if type(foundation_year) is list:
                for date in foundation_year:
                    if date['@status'] == 'C':
                        official_journal.foundation_year = date['@date'][:4]
            else:
                if foundation_year['@status'] == 'C':
                    official_journal.foundation_year = foundation_year['@date'][:4]
            official_journal.creator = user
        official_journal.save()
        return official_journal

    except Exception as e:
        error = JournalLoadError()
        error.step = "Official journal record creation error"
        error.description = str(e)[:509]
        error.save()


