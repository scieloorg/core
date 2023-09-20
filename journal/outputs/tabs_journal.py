from datetime import datetime

from journal.exceptions import (
    AddIssnScieloToTabsError,
    AddIssnsToTabsError,
)

from journal.models import (
    Journal,
    OfficialJournal,
    SciELOJournal,
)


def get_date():
    return datetime.utcnow().strftime("%Y-%m-%d")


def add_extraction_date(dict_data={}):
    dict_data["extraction date"] = get_date()


def add_issn_scielo(obj, dict_data={}):
    try:
        dict_data["ISSN SciELO"] = obj.issn_scielo
    except AttributeError as e:
        raise AddIssnScieloToTabsError(e, obj)


def add_issns(obj, dict_data={}):
    try:
        issn = None
        if type(obj) is OfficialJournal:
            issn = obj
        elif type(obj) is Journal:
            issn = obj.official
        elif type(obj) is SciELOJournal:
            issn = obj.journal.official
        dict_data["ISSN's"] = ";".join([issn.issn_print, issn.issn_electronic, issn.issnl])
    except AttributeError as e:
        raise AddIssnsToTabsError(e, obj)


def get_tabs_journal(obj, dict_data={}):
    get_issn_scielo(obj, dict_data)
    get_collection(obj, dict_data)

