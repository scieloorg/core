from core.models import Language
from institution.models import Institution

from ..models import Collection, OfficialJournal, Journal, SciELOJournal, Mission, Sponsor


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
    mission,
    sponsor,
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
    get_or_create_mission(mission=mission, journal=journal)
    get_or_create_sponso(sponsor=sponsor, journal=journal)    


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


def get_or_create_sponso(sponsor, journal):
    if sponsor and isinstance(sponsor, list):
        for s in sponsor:
            name = extract_value([s])
            ## FIXME
            ## Sponso de diferentes formas (insta_name e insta_acronym)
            ## Ex: 
            ## CNPq
            ## Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira
            ## Fundação Getulio Vargas/ Escola de Administração de Empresas de São Paulo
            ## CNPq - Conselho Nacional de Desenvolvimento Científico e Tecnológico (PIEB) 
            obj, created = Sponsor.objects.get_or_create(
                page=journal,
                institution=Institution.get_or_create(
                    inst_name=name,
                    inst_acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    location=None,
                    official=None,
                    is_official=None,
                )
            )