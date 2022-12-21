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
        official_journal = requests.get(
            f"http://{collection}/scielo.php?script=sci_serial&pid={issn}&lng=es&nrm=iso&debug=xml", timeout=10)
        return xmltodict.parse(official_journal.text)

    except Exception as e:
        error = ProcessingError()
        error.item = f"Error getting the ISSN {issn} of the {collection} collection"
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

        official_journal = OfficialJournal.get_or_create(title, foundation_year, issn_print,
                                                         issn_electronic, issnl, user)

        return official_journal

    except Exception as e:
        error = ProcessingError()
        error.item = f"Error getting or creating official journal for {journal_xml['SERIAL']['ISSN_AS_ID']}"
        error.step = "Official journal record creation error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def get_scielo_journal(user, journal_xml):
    try:
        official_journal = get_official_journal(user, journal_xml)
        issn_scielo = official_journal.issnl
        short_title = journal_xml['SERIAL']['TITLEGROUP']['SHORTTITLE']
        scielo_journal = ScieloJournal.get_or_create(official_journal, issn_scielo, short_title, user)

        journal_title = journal_xml['SERIAL']['TITLEGROUP']['TITLE']
        scielo_journal.panels_title.append(ScieloJournalTitle.get_or_create(scielo_journal, journal_title, user))

        mission_text = journal_xml['SERIAL']['MISSION']
        language = journal_xml['SERIAL']['CONTROLINFO']['LANGUAGE']
        scielo_journal.panels_mission.append(Mission.get_or_create(scielo_journal, issn_scielo, mission_text,
                                                                   language, user))

        institution_name = journal_xml['SERIAL']['PUBLISHERS']['PUBLISHER']['NAME']
        # the other parameters are not available in the XML file
        scielo_journal.panels_publisher.append(
            Institution.get_or_create(
                inst_name=institution_name,
                inst_acronym='',
                level_1='',
                level_2='',
                level_3='',
                location=None
            )
        )
        scielo_journal.creator = user
        scielo_journal.save()
        return scielo_journal

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
            get_scielo_journal(user, journal_xml)
