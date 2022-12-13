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


def get_scielo_journal(user, journal_xml):
    try:
        official_journal = get_official_journal(user, journal_xml)
        scielo_journals = ScieloJournal.objects.filter(official=official_journal)
        try:
            scielo_journal = scielo_journals[0]
        except IndexError:
            scielo_journal = ScieloJournal()
            scielo_journal.official = official_journal
            scielo_journal.short_title = journal_xml['SERIAL']['TITLEGROUP']['SHORTTITLE']
            scielo_journal.save()
            journal_title = journal_xml['SERIAL']['TITLEGROUP']['TITLE']
            scielo_journal_titles = ScieloJournalTitle.objects.filter(journal_title=journal_title)
            try:
                scielo_journal_title = scielo_journal_titles[0]
            except IndexError:
                scielo_journal_title = ScieloJournalTitle()
                scielo_journal_title.journal_title = journal_title
                scielo_journal_title.page = scielo_journal
                scielo_journal_title.save()
            scielo_journal.panels_title.append(scielo_journal_title)
            mission_text = journal_xml['SERIAL']['MISSION']
            scielo_missions = Mission.objects.filter(text=mission_text)
            try:
                scielo_mission = scielo_missions[0]
            except IndexError:
                scielo_mission = Mission()
                scielo_mission.text = mission_text
                scielo_mission.language = journal_xml['SERIAL']['CONTROLINFO']['LANGUAGE']
                scielo_mission.page = scielo_journal
                scielo_mission.save()
            scielo_journal.panels_mission.append(scielo_mission)
            institution_name = journal_xml['SERIAL']['PUBLISHERS']['PUBLISHER']['NAME']
            institutions = Institution.objects.filter(name=institution_name)
            try:
                institution = institutions[0]
            except IndexError:
                institution = Institution()
                institution.name = institution_name
                institution.save()
            history = InstitutionHistory()
            history.institution = institution
            history.page = scielo_journal
            history.save()
            scielo_journal.panels_publisher.append(history)
            scielo_journal.creator = user
            scielo_journal.save()
        return scielo_journal

    except Exception as e:
        error = JournalLoadError()
        error.step = "SciELO journal record creation error"
        error.description = str(e)[:509]
        error.save()


def load(user):
    for collection in get_collection():
        for issn in get_issn(collection):
            journal_xml = get_journal_xml(collection, issn)
            get_scielo_journal(user, journal_xml)
