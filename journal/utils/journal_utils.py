import re
from core.models import Language
from institution.models import Institution
from vocabulary.models import Vocabulary
from ..models import (
    Collection,
    OfficialJournal,
    Journal,
    SciELOJournal,
    Mission,
    Sponsor,
    SubjectDescriptor,
    Subject,
    Standard,
    WebOfKnowledge,
    WebOfKnowledgeSubjectCategory,
)


def create_or_update_journal(
    title,
    issn_scielo,
    short_title,
    other_titles,
    submission_online_url,
    open_access,
    issn_print_or_electronic,
    type_issn,
    current_issn,
    user,
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
    return journal


def create_or_update_scielo_journal(
    journal, collection, issn_scielo, journal_acron, user
):
    issnl = extract_value(issn_scielo)
    scielo_journal = SciELOJournal.create_or_update(
        user=user,
        collection=get_collection(collection),
        issn_scielo=issnl,
        journal_acron=extract_value(journal_acron),
        journal=journal,
    )
    return scielo_journal


def create_scope(
    journal,
    mission,
    sponsor,
    subject_descriptors,
    subject,
    wos_scie,
    wos_ssci,
    wos_ahci,
    wos_areas,
    user,
):
    get_or_create_mission(journal=journal, mission=mission, user=user)
    get_or_create_sponso(journal=journal, sponsor=sponsor, user=user)
    get_or_create_subject_descriptor(
        journal=journal,
        subject_descriptors=subject_descriptors,
        user=user,
    )
    create_or_update_subject(journal=journal, subject=subject, user=subject)
    create_or_update_wos_db(
        journal=journal,
        wos_scie=wos_scie,
        wos_ssci=wos_ssci,
        wos_ahci=wos_ahci,
        user=user,
    )
    get_or_update_wos_areas(journal=journal, wos_areas=wos_areas, user=user)


def create_interoperation(
    journal, indexed_at, secs_code, medline_code, medline_short_title, user
):
    journal.secs_code = extract_value(secs_code)
    journal.medline_code = extract_value(medline_code)
    journal.medline_short_title = extract_value(medline_short_title)


def create_information(
    journal,
    frequency,
    publishing_model,
    text_language,
    abstract_language,
    standard,
    vocabulary,
    alphabet,
    classification,
    national_code,
    type_of_literature,
    treatment_level,
    level_of_publication,
    user,
):
    create_or_update_journal_languages(
        journal=journal,
        language_data=text_language,
        language_type="text",
        user=user,
    )
    create_or_update_journal_languages(
        journal=journal,
        language_data=abstract_language,
        language_type="abstract",
        user=user,
    )
    get_or_create_vocabulary(vocabulary=vocabulary, journal=journal, user=user)
    create_or_update_standard(standard=standard, journal=journal, user=user)
    journal.frequency = extract_value(frequency)
    journal.publishing_model = extract_value(publishing_model)
    journal.alphabet = extract_value(alphabet)
    journal.classification = extract_value(classification)
    journal.national_code = extract_value(national_code)
    journal.type_of_literature = extract_value(type_of_literature)
    journal.treatment_level = extract_value(treatment_level)
    if len(extract_value(level_of_publication)) < 3:
        journal.level_of_publication = extract_value(level_of_publication)


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


# colocar em outro arquivo
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


# colocar em outro arquivo
def extract_value(value):
    if value and isinstance(value, list):
        if len(value) > 1:
            return [x.get("_") for x in value]
        return [x.get("_") for x in value][0]


# colocar em outro arquivo
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


def get_or_create_mission(mission, journal, user):
    if mission and isinstance(mission, list):
        missions = extract_value_mission(mission=mission)
        for m in missions:
            obj, created = Mission.objects.get_or_create(
                journal=journal,
                rich_text=m.get("mission"),
                language=Language.get_or_create(code2=m.get("lang")),
                creator=user,
            )


def get_or_create_sponso(sponsor, journal, user):
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
                    user=user,
                ),
            )


def get_or_create_subject_descriptor(subject_descriptors, journal, user):
    data = []
    if subject_descriptors:
        sub_desc = extract_value(subject_descriptors)
        if isinstance(sub_desc, str):
            sub_desc = [sub_desc]
        for s in sub_desc:
            for word in re.split(",|;", s):
                word = word.strip()
                obj, created = SubjectDescriptor.objects.get_or_create(
                    value=word,
                    creator=user,
                )
                data.append(obj)
        journal.subject_descriptor.set(data)


def create_or_update_subject(subject, journal, user):
    data = []
    if subject:
        sub = extract_value(subject)
        if isinstance(sub, str):
            sub = [sub]
        for s in sub:
            obj = Subject.create_or_update(code=s, user=user)
            data.append(obj)
        journal.subject.set(data)


def create_or_update_journal_languages(language_data, journal, language_type, user):
    data = []
    if language_type:
        langs = extract_value(language_data)
        if isinstance(langs, str):
            langs = [langs]
        for l in langs:
            obj = Language.get_or_create(code2=l, creator=user)
            data.append(obj)

        if language_type == "text":
            journal.text_language.set(data)
        elif language_type == "abstract":
            journal.abstract_language.set(data)


def get_or_create_vocabulary(vocabulary, journal, user):
    if vocabulary:
        v = extract_value(vocabulary)
        obj = Vocabulary.get_or_create(name=None, acronym=v, user=user)
        journal.vocabulary = obj


def create_or_update_standard(standard, journal, user):
    if standard:
        standard = extract_value(standard)
        obj = Standard.create_or_update(
            code=standard,
            user=user,
        )
        journal.standard = obj


def create_or_update_wos_db(journal, wos_scie, wos_ssci, wos_ahci, user):
    data = []
    for db in (wos_scie, wos_ssci, wos_ahci):
        wosdb = extract_value(db)
        if wosdb:
            obj = WebOfKnowledge.create_or_update(
                code=wosdb,
                user=user,
            )
            data.append(obj)
    journal.wos_db.set(data)


def get_or_update_wos_areas(journal, wos_areas, user):
    data = []
    if wos_areas:
        areas = extract_value(wos_areas)
        if isinstance(areas, str):
            areas = [areas]
        for a in areas:
            for word in re.split(",|;", a):
                obj, created = WebOfKnowledgeSubjectCategory.objects.get_or_create(
                    value=word,
                    creator=user,
                )
                data.append(obj)
        journal.wos_area.set(data)
