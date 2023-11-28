import re
import sys
from datetime import datetime

from django.db.models import Q

from core.models import Language, License
from institution.models import CopyrightHolder, Owner, Publisher, Sponsor
from journal.models import (
    Annotation,
    Collection,
    CopyrightHolderHistory,
    IndexedAt,
    Journal,
    JournalEmail,
    JournalHistory,
    JournalParallelTitles,
    Mission,
    OfficialJournal,
    OwnerHistory,
    PublisherHistory,
    SciELOJournal,
    SponsorHistory,
    Standard,
    Subject,
    SubjectDescriptor,
    WebOfKnowledge,
    WebOfKnowledgeSubjectCategory,
)
from location.models import City, CountryName, Location, State, Country
from reference.models import JournalTitle
from vocabulary.models import Vocabulary

from .am_data_extraction import (
    extract_issn_print_electronic,
    extract_value,
    extract_value_from_journal_history,
    extract_value_mission,
    parse_date_string,
)

from tracker.models import UnexpectedEvent


def create_or_update_journal(
    title,
    short_title,
    other_titles,
    submission_online_url,
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
    )
    return journal


def create_or_update_scielo_journal(
    journal, collection, issn_scielo, journal_acron, status, journal_history, user
):
    issn_scielo = extract_value(issn_scielo)
    code_status = extract_value(status)
    scielo_journal = SciELOJournal.create_or_update(
        user=user,
        collection=get_collection(collection),
        issn_scielo=issn_scielo,
        journal_acron=extract_value(journal_acron),
        journal=journal,
        code_status=code_status,
    )
    get_or_create_journal_history(
        scielo_journal=scielo_journal, journal_history=journal_history
    )
    return scielo_journal


def update_panel_scope_and_about(
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
    get_or_create_sponsor(journal=journal, sponsor=sponsor, user=user)
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


def update_panel_interoperation(
    journal, indexed_at, secs_code, medline_code, medline_short_title, user
):
    get_or_create_indexed_at(journal, indexed_at=indexed_at, user=user)
    journal.secs_code = extract_value(secs_code)
    journal.medline_code = extract_value(medline_code)
    journal.medline_short_title = extract_value(medline_short_title)


def update_panel_information(
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


def update_panel_institution(
    journal,
    publisher,
    copyright_holder,
    address,
    electronic_address,
    publisher_country,
    publisher_state,
    publisher_city,
    user,
):
    """
    Ex eletronic_addrees:
        [{"_": "maritzal@telcel.net.ve"}, {"_": " fbengoanutricion@cantv.net"}]
        [{"_": "info@asppr.net"}] 
        [{"_": "CLEIejEditor@fing.edu.uy"}]
    """
    location = create_or_update_location(
        journal,
        address,
        publisher_country,
        publisher_state,
        publisher_city,
        user,
    )
    electronic_address = extract_value(electronic_address)
    if isinstance(electronic_address, str):
        electronic_address = [electronic_address]

    for item in electronic_address:
        try:
            item = item and item.strip().lower()
            JournalEmail.objects.get(journal=journal, email=item)
        except JournalEmail.DoesNotExist:
            JournalEmail.objects.create(journal=journal, email=item)

    publisher = extract_value(publisher)

    if isinstance(publisher, str):
        publisher = [publisher]

    if publisher:
        for p in publisher:
            if p:
                journal.contact_name = p
                publisher = Publisher.create_or_update(
                    inst_name=p,
                    user=user,
                    location=location,
                    url=None,
                    inst_acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    official=None,
                    is_official=None,
                )
                publisher_history = PublisherHistory.get_or_create(
                    institution=publisher,
                    user=user,
                )
                publisher_history.journal = journal
                publisher_history.save()
                owner = Owner.create_or_update(
                    inst_name=p,
                    user=user,
                    location=location,
                    url=None,
                    inst_acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    official=None,
                    is_official=None,
                )
                owner_history = OwnerHistory.get_or_create(
                    institution=owner,
                    user=user,
                )
                owner_history.journal = journal
                owner_history.save()

    get_or_create_copyright_holder(
        journal=journal, copyright_holder_name=copyright_holder, user=user
    )


def update_panel_website(
    journal,
    url_of_the_journal,
    url_of_submission_online,
    url_of_the_main_collection,
    license_of_use,
    user,
):
    journal.journal_url = extract_value(url_of_the_journal)
    journal.collection_main_url = extract_value(url_of_the_main_collection)
    journal.submission_online_url = extract_value(url_of_submission_online)
    license_type = extract_value(license_of_use)
    if license_type:
        license = License.create_or_update(license_type=license_type, user=user)
        journal.use_license = license


def update_panel_notes(
    journal,
    notes,
    creation_date,
    update_date,
    user,
):
    """
    Ex notes:
        [{'_': 'Editor:'}, {'_': 'Denis Coitinho Silveira'}, {'_': 'Rua Lobo da Costa, 270/501'}, {'_': '90050-110'}, {'_': 'UNISINOS - Universidade do Vale do Rio dos Sinos'}, {'_': 'Porto Alegre'}, {'_': 'RS'}, {'_': 'Brasil'}, {'_': '51 32269513; 51 983107257'}, {'_': 'deniscoitinhosilveira@gmail.com'}]
        [{'_': 'Iniciou no v12n1'}]
    Ex creation_date e update_date:
        [{'_': '20060208'}]
        [{'_': '20120824'}]
    """
    notes = extract_value(notes)
    if notes:
        try:
            creation_date = datetime.strptime(extract_value(creation_date), "%Y%m%d")
        except ValueError:
            creation_date = None
        try:
            update_date = datetime.strptime(extract_value(update_date), "%Y%m%d")
        except ValueError:
            update_date = None

        if isinstance(notes, str):
            notes = [notes]
        n = "\n".join(notes)
        obj = Annotation.create_or_update(
            journal=journal,
            notes=n,
            creation_date=creation_date,
            update_date=update_date,
            user=user,
        )


def update_panel_legacy_compatibility_fields(
    journal,
    center_code,
    identification_number,
    ftp,
    user_subscription,
    subtitle,
    section,
    has_supplement,
    is_supplement,
    acronym_letters,
):
    user_subs = extract_value(user_subscription)
    if user_subs and 2 <= len(user_subs) <= 3:
        journal.user_subscription = user_subs
    journal.center_code = extract_value(center_code)
    journal.identification_number = extract_value(identification_number)
    journal.ftp = extract_value(ftp)
    journal.subtitle = extract_value(subtitle)
    journal.section = extract_value(section)
    journal.has_supplement = extract_value(has_supplement)
    journal.is_supplement = extract_value(is_supplement)
    journal.acronym_letters = extract_value(acronym_letters)


def create_or_update_official_journal(
    title,
    new_title,
    old_title,
    issn_print_or_electronic,
    issn_scielo,
    type_issn,
    current_issn,
    initial_date,
    initial_volume,
    initial_number,
    terminate_date,
    final_volume,
    final_number,
    iso_short_title,
    parallel_titles,
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
    issn_scielo = extract_value(issn_scielo)

    if type_issn and current_issn:
        for item in type_issn:
            item["t"] = item.pop("_")
        type_issn[0].update(current_issn[0])
    issn = issn_print_or_electronic or type_issn
    issn_print, issn_electronic = extract_issn_print_electronic(
        issn_print_or_electronic=issn
    )

    official_journal = OfficialJournal.create_or_update(
        user=user,
        issn_print=issn_print,
        issn_electronic=issn_electronic,
        issnl=None,
        title=title,
        foundation_year=foundation_year,
    )
    get_or_update_parallel_titles(
        of_journal=official_journal, parallel_titles=parallel_titles
    )
    # official_journal.new_title = extract_value(new_title)
    # official_journal.old_title = extract_value(old_title)
    official_journal.iso_short_title = extract_value(iso_short_title)

    initial_date = extract_value(initial_date)
    terminate_date = extract_value(terminate_date)
    official_journal.initial_year, official_journal.initial_month = parse_date_string(
        date=initial_date
    )
    official_journal.initial_number = extract_value(initial_number)
    official_journal.initial_volume = extract_value(initial_volume)

    year, month = parse_date_string(date=terminate_date)
    official_journal.terminate_year = year
    official_journal.terminate_month = month

    official_journal.final_number = extract_value(final_number)
    official_journal.final_volume = extract_value(final_volume)
    official_journal.save()
    return official_journal


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


def get_or_create_sponsor(sponsor, journal, user):
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
            if name:
                sponsor = Sponsor.create_or_update(
                    inst_name=name,
                    user=user,
                    inst_acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    location=None,
                    official=None,
                    is_official=None,
                    url=None,
                )
                sponsor_history = SponsorHistory.get_or_create(
                    institution=sponsor,
                    user=user,
                )
                sponsor_history.journal = journal
                sponsor_history.save()


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
            if s:
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
            obj = Subject.get(code=s,)
            data.append(obj)
        journal.subject.set(data)


def create_or_update_journal_languages(language_data, journal, language_type, user):
    data = []
    if language_data:
        langs = extract_value(language_data)
        if isinstance(langs, str):
            langs = [langs]
        for l in langs:
            obj = Language.get_or_create(code2=l, creator=user)
            if obj:
                data.append(obj)

        if language_type == "text":
            journal.text_language.set(data)
        elif language_type == "abstract":
            journal.abstract_language.set(data)


def get_or_create_vocabulary(vocabulary, journal, user):
    if vocabulary:
        v = extract_value(vocabulary)
        obj = Vocabulary.get(acronym=v)
        journal.vocabulary = obj


def create_or_update_standard(standard, journal, user):
    if standard:
        standard = extract_value(standard)
        journal.standard = Standard.get(standard)


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
        for value in areas:
            try:
                obj = WebOfKnowledgeSubjectCategory.objects.get(
                    value=value,
                )
            except WebOfKnowledgeSubjectCategory.DoesNotExist as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "function": "am_to_core.get_or_update_wos_areas",
                        "wos_areas": value,
                    },
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


def create_or_update_location(
    journal,
    address,
    publisher_country,
    publisher_state,
    publisher_city,
    user,
):
    """
    Exemplo de entradas de publisher_country, publisher_state:
    publisher_state:
        [{'_': 'Distrito Capital'}], [{'_': 'DF'}] e None
    publisher_country:
        [{'_': 'CO'}], [{'_': 'Colombia}] e None
    address:
        [{'_': 'Rua Felizardo, 750 Jardim Botânico'}, {'_': 'CEP: 90690-200'}, {'_': 'RS - Porto Alegre'}, {'_': '(51) 3308 5814'}]
    """

    #O valor publisher_country pode fornecer tanto 
    #o nome completo do país quanto o acrônimo do país.
    country_value = extract_value(publisher_country)
    country = None
    for item in Country.standardize(country_value, user=user):
        country = item.get("country")

    name_city = extract_value(publisher_city)
    city = None
    for item in City.standardize(name_city, user=user):
        city = item.get("city")

    #O valor publisher_state pode fornecer tanto 
    #o nome completo do estado quanto o acrônimo do estado.
    state_value = extract_value(publisher_state)
    state = None
    for item in State.standardize(state_value, user=user):
        state = item.get("state")

    location = Location.create_or_update(
        user=user,
        country=country,
        state=state,
        city=city,
    )
    journal.contact_location = location

    address = extract_value(address)
    if address:
        if isinstance(address, str):
            address = [address]
        address = "\n".join(address)

    journal.contact_address = address

    return location


def get_or_update_parallel_titles(of_journal, parallel_titles):
    data = []
    if parallel_titles:
        titles = extract_value(parallel_titles)
        if isinstance(titles, str):
            titles = [titles]
        for title in titles:
            obj, created = JournalParallelTitles.objects.get_or_create(
                text=title,
            )
            data.append(obj)
        of_journal.parallel_titles.set(data)


def get_or_create_journal_history(scielo_journal, journal_history):
    data = []
    if journal_history:
        journal_history = extract_value_from_journal_history(journal_history)
        for jh in journal_history:
            JournalHistory.am_to_core(
                scielo_journal,
                initial_year=jh.get("initial_year"),
                initial_month=jh.get("initial_month"),
                initial_day=jh.get("initial_day"),
                final_year=jh.get("final_year"),
                final_month=jh.get("final_month"),
                final_day=jh.get("final_day"),
                event_type=jh.get("event_type"),
                interruption_reason=jh.get("interruption_reason"),
            )


def get_or_create_copyright_holder(journal, copyright_holder_name, user):
    """
    Ex copyright_holder_name:
        [{'_': 'Departamento de História da Universidade Federal Fluminense - UFF'}]
    """
    copyright_holder_name = extract_value(copyright_holder_name)
    if copyright_holder_name:
        copyright_holder = CopyrightHolder.create_or_update(
            inst_name=copyright_holder_name,
            user=user,
            inst_acronym=None,
            level_1=None,
            level_2=None,
            level_3=None,
            location=None,
            official=None,
            is_official=None,
            url=None,
        )
        copyright_holder_history = CopyrightHolderHistory.get_or_create(
            institution=copyright_holder,
            user=user,
        )
        copyright_holder_history.journal = journal
        copyright_holder_history.save()
