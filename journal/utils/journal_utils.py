import re
from django.db.models import Q
from core.models import Language
from institution.models import Institution
from vocabulary.models import Vocabulary
from reference.models import JournalTitle
from .funcs_extract_am import (
    extract_issn_print_electronic,
    extract_value,
    extract_value_mission,
)
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
    IndexedAt,
)


def create_or_update_journal(
    title,
    short_title,
    other_titles,
    submission_online_url,
    open_access,
    official_journal,
    user,
):
    title = extract_value(title)
    other_titles = get_or_create_other_titles(other_titles=other_titles, user=user)

    journal = Journal.create_or_update(
        user=user,
        official_journal=official_journal,
        title=title,
        short_title=extract_value(short_title),
        other_titles=other_titles,
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
    create_or_update_subject(journal=journal, subject=subject, user=user)
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
    get_or_create_indexed_at(journal, indexed_at=indexed_at, user=user)
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
    new_title,
    old_title,
    issn_print_or_electronic,
    issn_scielo,
    type_issn,
    current_issn,
    user,
    foundation_year=None,
):
    """
    Ex type_issn:
        [{"_": "ONLIN"}]
    Ex current_issn:
        [{"_": "1676-5648"}]
    """
    title = extract_value(title)
    issnl = extract_value(issn_scielo)

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
    obj.new_title = extract_value(new_title)
    obj.old_title = extract_value(old_title)
    obj.save()
    return obj


def get_collection(collection):
    try:
        return Collection.objects.get(code=collection)
    except Collection.DoesNotExist:
        return None


def get_or_create_other_titles(other_titles, user):
    data = []
    if other_titles:
        ot = extract_value(other_titles)
        if isinstance(ot, str):
            ot = [ot]
        for t in ot:
            obj, created = JournalTitle.objects.get_or_create(
                title=t,
                creator=user,
            )
            data.append(obj)
        # journal.other_titles.set(data)
        return data


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
    """
    subject_descriptors:
        [{'_': 'ECONOMIA, TEORIA ECONÔMICA,  HISTÓRIA ECONÔMICA,  ECONOMIA MONETÁRIA E FISCAL, CRESCIMENTO, FLUTUAÇÕES E PLANEJAMENTO ECONÔMICO'}]
        [{'_': 'MEDICINA'}, {'_': 'PSIQUIATRIA'}, {'_': 'SAUDE MENTAL'}]
        [{'_': 'AGRONOMIA; FITOPATOLOGIA; FITOSSANIDADE'}]
    """
    data = []
    if subject_descriptors:
        sub_desc = extract_value(subject_descriptors)
        if isinstance(sub_desc, str):
            sub_desc = [sub_desc]
        for s in sub_desc:
            # Em alguns casos, subject_descriptors vem separado por "," ou ";"
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
    """
    wos_scie, wos_ssci, wos_ahci:
        [{'_': 'SCIE'}]  # Exemplo para wos_scie
        [{'_': 'SSCI'}]  # Exemplo para wos_ssci
        [{'_': 'A&HCI'}]  # Exemplo para wos_ahci
    """
    data = []
    # Haverá um único valor entre os três (wos_scie, wos_ssci, wos_ahci)
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
    """
    wos_areas:
        [{'_': 'EDUCATION & EDUCATIONAL RESEARCH'}, {'_': 'HISTORY'}, {'_': 'PHILOSOPHY'}, {'_': 'POLITICAL SCIENCE'}, {'_': 'SOCIOLOGY'}]
        [{'_': 'LANGUAGE & LINGUISTICS'}, {'_': 'LITERATURE, GERMAN, DUTCH, SCANDINAVIAN'}]
    """
    data = []
    if wos_areas:
        areas = extract_value(wos_areas)
        if isinstance(areas, str):
            areas = [areas]
        for a in areas:
            obj, created = WebOfKnowledgeSubjectCategory.objects.get_or_create(
                value=a,
                creator=user,
            )
            data.append(obj)
        journal.wos_area.set(data)


def get_or_create_indexed_at(journal, indexed_at, user):
    """
    indexed_at:
        [{'_': 'Index to Dental Literature'}, {'_': 'LILACS'}, {'_': 'Base de Dados BBO'}, {'_': "Ulrich's"}, {'_': 'Biological Abstracts'}, {'_': 'Medline'}]
    """
    data = []
    if indexed_at:
        indexed = extract_value(indexed_at)
        if isinstance(indexed, str):
            indexed = [indexed]
        for i in indexed:
            obj = IndexedAt.objects.filter(
                Q(name__icontains=i) | Q(acronym__icontains=i)
            ).first()
            if not obj:
                obj = IndexedAt.create_or_update(
                    name=i,
                    user=user,
                )
            data.append(obj)
        journal.indexed_at.set(data)
