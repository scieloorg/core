from datetime import datetime

from journal.exceptions import (
    AddIssnScieloToTabsError,
    AddIssnsToTabsError,
    AddTitleAtScieloError,
    AddTitleThematicAreasError,
    AddTitleCurrentStatusError,
)


def get_date():
    """
    Obtem a data de execução do código

    Returns
    -------
    str
        2023-08-30
    """
    return datetime.utcnow().strftime("%Y-%m-%d")


def add_extraction_date(dict_data={}):
    """
    Adiciona a data de extração dos dados em um dicionário

    Parameters
    ----------
    dict_data : dict
        Dicionário que receberá os dados

    Returns
    -------
    dict_data : dict
        Dicionário com dados adicionados, como por exemplo:
        {
            "extraction date": "1900-01-01"
        }
    """
    dict_data["extraction date"] = get_date()


def add_issn_scielo(scielo_journal, dict_data={}):
    """
    Adiciona o ISSN SciELO em um dicionário

    Parameters
    ----------
    scielo_journal : journal.models.SciELOJournal
        Objeto com dados de um periódico SciELO

    dict_data : dict
        Dicionário que receberá os dados

    Returns
    -------
    dict_data : dict
        Dicionário com dados adicionados, como por exemplo:
        {
            "ISSN SciELO": "0000-0000"
        }
    """
    try:
        dict_data["ISSN SciELO"] = scielo_journal.issn_scielo
    except AttributeError as e:
        raise AddIssnScieloToTabsError(e, scielo_journal)


def add_issns(scielo_journal, dict_data={}):
    """
    Adiciona uma série de ISSN's em um dicionário

    Parameters
    ----------
    scielo_journal : journal.models.SciELOJournal
        Objeto com dados de um periódico SciELO

    dict_data : dict
        Dicionário que receberá os dados

    Returns
    -------
    dict_data : dict
        Dicionário com dados adicionados, como por exemplo:
        {
            "ISSN's": "0000-0000;1111-1111;2222-2222"
        }
    """
    try:
        dict_data["ISSN's"] = ";".join([
            scielo_journal.journal.official.issn_print,
            scielo_journal.journal.official.issn_electronic,
            scielo_journal.journal.official.issnl
        ])
    except AttributeError as e:
        raise AddIssnsToTabsError(e, scielo_journal)


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


def add_tabs_journal(obj, collection, dict_data={}):
    add_extraction_date(dict_data)
    dict_data.update({
        "study unit": "journal",
        "collection": collection
    })
    add_issn_scielo(obj, dict_data)
    add_issns(obj, dict_data)
