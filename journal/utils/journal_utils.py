from django.core.exceptions import ObjectDoesNotExist

from ..models import Collection, OfficialJournal, ScieloJournal


def get_or_create_scielo_journal(
    title,
    issn_scielo,
    short_title,
    submission_online_url,
    open_access,
    issn_print_or_electronic,
    collection,
    user,
):
    obj = ScieloJournal.get_or_create(
        official_journal=get_or_create_official_journal(
            title=extract_value(title),
            issn_print_or_electronic=issn_print_or_electronic,
            user=user,
        ),
        title=extract_value(title),
        issn_scielo=extract_value(issn_scielo),
        short_title=extract_value(short_title),
        submission_online_url=extract_value(submission_online_url),
        open_access=extract_value(open_access),
        collection=get_collection(collection),
        user=user,
    )
    print(obj)


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
    obj = OfficialJournal.get_or_create(
        title=title,
        issn_print=issn_print,
        issn_electronic=issn_electronic,
        user=user,
        foundation_year=foundation_year,
        issnl=issnl,
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
