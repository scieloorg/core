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


    try:
        dict_data["ISSN SciELO"] = obj.issn_scielo
    except AttributeError as e:
        print(f"There is no information about 'issn_scielo' in the object {obj}")


def get_collection(obj, dict_data={}):
    try:
        dict_data["collection"] = obj.collection.acron3
    except AttributeError:
        try:
            dict_data["collection"] = obj.journal.collection.all()[0].acron3
        except AttributeError:
            print(f"There is no information about 'collection' in the object {obj}")


def get_tabs_journal(obj, dict_data={}):
    get_issn_scielo(obj, dict_data)
    get_collection(obj, dict_data)

