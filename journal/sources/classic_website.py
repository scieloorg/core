import sys
import json

import requests
import xmltodict

from collection.models import Collection
from institution.models import Institution, InstitutionHistory
from tracker.models import UnexpectedEvent

from journal.models import Journal, Mission, OfficialJournal, SciELOJournal


def get_issn(collection):
    try:
        collections = requests.get(
            f"http://{collection}/scielo.php?script=sci_alphabetic&lng=es&nrm=iso&debug=xml",
            timeout=10,
        )
        data = xmltodict.parse(collections.text)

        for issn in data["SERIALLIST"]["LIST"]["SERIAL"]:
            try:
                yield issn["TITLE"]["@ISSN"]
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail=dict(
                        function="journal.sources.classic_website.get_issn",
                        message=f"ISSN's list of {collection} collection error",
                    ),
                )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="journal.sources.classic_website.get_issn",
            ),
        )


def get_journal_xml(collection, issn):
    try:
        official_journal = requests.get(
            f"http://{collection}/scielo.php?script=sci_serial&pid={issn}&lng=es&nrm=iso&debug=xml",
            timeout=10,
        )
        return xmltodict.parse(official_journal.text)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="journal.sources.classic_website.get_journal_xml",
                message=f"Error getting the ISSN {issn} of the {collection} collection",
            ),
        )


def get_official_journal(user, journal_xml):
    try:
        title = journal_xml["SERIAL"]["TITLEGROUP"]["TITLE"]
        # this value are not available in the XML file
        foundation_year = None
        issns = journal_xml["SERIAL"]["TITLE_ISSN"]
        issns_list = issns if type(issns) is list else [issns]
        issn_print = None
        issn_electronic = None

        for issn in issns_list:
            if issn["@TYPE"] == "PRINT":
                issn_print = issn["#text"]
            if issn["@TYPE"] == "ONLIN":
                issn_electronic = issn["#text"]

        official_journal = OfficialJournal.create_or_update(
            user=user,
            issn_print=issn_print,
            issn_electronic=issn_electronic,
            title=title,
            foundation_year=foundation_year,
        )

        return official_journal

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="journal.sources.classic_website.get_official_journal",
                message=f"Error getting or creating official journal for {journal_xml['SERIAL']['ISSN_AS_ID']}",
            ),
        )


def create_journal(user, journal_xml, collection):
    try:
        official_journal = get_official_journal(user, journal_xml)
        issn_scielo = journal_xml["SERIAL"]["ISSN_AS_ID"]
        title = journal_xml["SERIAL"]["TITLEGROUP"]["TITLE"]
        short_title = journal_xml["SERIAL"]["TITLEGROUP"]["SHORTTITLE"]
        journal = Journal.create_or_update(
            user=user,
            official_journal=official_journal,
            title=title,
            short_title=short_title,
        )

        scielo_journal = SciELOJournal.create_or_update(
            user=user,
            collection=collection,
            # FIXME
            # journal_acron=journal_acron,
            issn_scielo=issn_scielo,
            journal=journal,
        )

        mission_rich_text = journal_xml["SERIAL"]["MISSION"]
        language = journal_xml["SERIAL"]["CONTROLINFO"]["LANGUAGE"]
        journal.panels_mission.append(
            Mission.create_or_update(
                user,
                journal,
                language,
                mission_rich_text,
            )
        )

        institution_name = journal_xml["SERIAL"]["PUBLISHERS"]["PUBLISHER"]["NAME"]
        # the other parameters are not available in the XML file
        institution = Institution.get_or_create(
            inst_name=institution_name,
            inst_acronym=None,
            level_1=None,
            level_2=None,
            level_3=None,
            location=None,
        )
        history = InstitutionHistory.get_or_create(
            institution=institution, initial_date=None, final_date=None
        )
        journal.panels_publisher.append(history)
        journal.creator = user
        journal.save()
        return journal

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail=dict(
                function="journal.sources.classic_website.create_journal",
                message=f"Error getting or creating SciELO journal for {journal_xml['SERIAL']['ISSN_AS_ID']}",
            ),
        )


def load(user):
    for collection in Collection.objects.all().iterator():
        try:
            for issn in get_issn(collection.domain):
                journal_xml = get_journal_xml(collection.domain, issn)
                create_journal(user, journal_xml, collection)
        except:
            pass
