from ..models import Collection, OfficialJournal, ScieloJournal
from ..models import Mission
from core.models import Language


def get_or_create_scielo_journal(
    title,
    issn_scielo,
    short_title,
    submission_online_url,
    open_access,
    issn_print_or_electronic,
    collection,
    mission,
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
    get_or_create_mission(mission=mission, journal=obj)


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
    except Collection.DoesNotExist:
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


def extract_value_mission(mission):
    """
    [
        {
            "l": "es",
            "_": "La RAE-eletr\u00f4nica tiene como misi\u00f3n fomentar la producci\u00f3n y la diseminaci\u00f3n del conocimiento en Administraci\u00f3n de Empresas."
        },
        {
            "l": "pt",
            "_": "A RAE-eletr\u00f4nica tem como miss\u00e3o fomentar a produ\u00e7\u00e3o e a dissemina\u00e7\u00e3o de conhecimento em Administra\u00e7\u00e3o de Empresas."
        },
        {
            "l": "en",
            "_": "RAE-eletr\u00f4nica's mission is to encourage the production and dissemination of Business Administration knowledge."
        }
    ]
    """

    return [{"lang": x.get("l"), "mission": x.get("_")} for x in mission]


def get_or_create_mission(mission, journal):
    if mission and isinstance(mission, list):
        missions = extract_value_mission(mission=mission)
        for m in missions:
            obj, created = Mission.objects.get_or_create(
                journal=journal,
                rich_text=m.get("mission"),
                language=Language.get_or_create(code2=m.get("lang")),
            )
