from django.core.exceptions import ObjectDoesNotExist

from ..models import Collection, Journal, OfficialJournal, SciELOJournal


def get_or_create_scielo_journal(
    title,
    issn_scielo,
    short_title,
    submission_online_url,
    open_access,
    issn_print_or_electronic,
    collection,
    user,
    journal_acron=None,
):
    journal = Journal.create_or_update(
        user=user,
        official_journal=get_or_create_official_journal(
            title=extract_value(title),
            issn_print_or_electronic=issn_print_or_electronic,
        ),
        title=extract_value(title),
        short_title=extract_value(short_title),
        submission_online_url=extract_value(submission_online_url),
        open_access=extract_value(open_access),
    )
    scielo_journal = SciELOJournal.create_or_update(
        user=user,
        collection=collection,
        issn_scielo=issn_scielo,
        journal_acron=journal_acron,
        journal=journal,
    )


def get_or_create_official_journal(
    title,
    issn_print_or_electronic,
    user,
    issnl=None,
    foundation_year=None,
):
    issn_print, issn_electronic = extract_issn_print_electronic(
        issn_print_or_electronic
    )
    obj = OfficialJournal.create_or_update(
        user=user,
        issn_print=issn_print,
        issn_electronic=issn_electronic,
        issnl=issnl,
        title=title,
        foundation_year=foundation_year,
    )
    return obj


def get_collection(collection):
    try:
        return Collection.objects.get(code=collection)
    except ObjectDoesNotExist:
        return None


def extract_issn_print_electronic(issn_print_or_electronic):
    issn_print = None
    issn_electronic = None

    if issn_print_or_electronic:
        for issn in issn_print_or_electronic:
            if issn["t"] == "PRINT":
                issn_print = issn["_"]
            elif issn["t"] == "ONLIN":
                issn_electronic = issn["_"]
    return issn_print, issn_electronic


def extract_value(value):
    if value and isinstance(value, list):
        return [x.get("_") for x in value][0]
