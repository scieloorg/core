from django.core.exceptions import ObjectDoesNotExist

from ..models import Collection, OfficialJournal, Journal, SciELOJournal


def create_or_update_scielo_journal(
    title,
    issn_scielo,
    short_title,
    submission_online_url,
    open_access,
    issn_print_or_electronic,
    type_issn,
    current_issn,
    collection,
    user,
    journal_acron=None,
):
    title = extract_value(title)
    issnl = extract_value(issn_scielo)

    journal = Journal.create_or_update(
        user=user,
        official_journal=create_or_update_official_journal(
            user=user,
            title=title,
            issn_print_or_electronic=issn_print_or_electronic,
            type_issn=type_issn,
            issnl=issnl,
            current_issn=current_issn,
        ),
        title=title,
        short_title=extract_value(short_title),
        submission_online_url=extract_value(submission_online_url),
        open_access=extract_value(open_access),
    )
    scielo_journal = SciELOJournal.create_or_update(
        user=user,
        collection=get_collection(collection),
        issn_scielo=issnl,
        journal_acron=extract_value(journal_acron),
        journal=journal,
    )


def create_or_update_official_journal(
    title,
    issn_print_or_electronic,
    type_issn,
    current_issn,
    user,
    issnl=None,
    foundation_year=None,
):
    """
    Ex type_issn:
         [{"_": "ONLIN"}]
    Ex current_issn:
        [{"_": "1676-5648"}]
    """

    if type_issn and current_issn:
        for item in type_issn:
            item["t"] = item.pop("_")
        type_issn[0].update(current_issn[0])

    issn = issn_print_or_electronic or type_issn
    issn_print, issn_electronic = extract_issn_print_electronic(
        issn_print_or_electronic=issn
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
