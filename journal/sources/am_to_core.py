import logging
import re
import sys
from datetime import datetime

from django.db.models import Q

from collection.exceptions import MainCollectionNotFoundError
from core.models import Language, License
from institution.models import CopyrightHolder, Owner, Publisher, Sponsor
from journal.models import (
    Annotation,
    Collection,
    CopyrightHolderHistory,
    IndexedAt,
    AdditionalIndexedAt,
    Journal,
    JournalEmail,
    JournalHistory,
    JournalParallelTitle,
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
    TitleInDatabase,
)
from location.models import City, CountryName, Location, State, Country
from reference.models import JournalTitle
from vocabulary.models import Vocabulary

from .am_data_extraction import (
    get_issns,
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
    
    update_title_in_database(user=user, journal=journal, code=secs_code, acronym="secs")
    update_title_in_database(user=user, journal=journal, code=medline_code, acronym="medline", title=medline_short_title)


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
    if electronic_address:
        for item in electronic_address:
            try:
                item = item and item.strip().lower()
                JournalEmail.objects.get(journal=journal, email=item)
            except JournalEmail.DoesNotExist:
                JournalEmail.objects.create(journal=journal, email=item)

    publisher = extract_value(publisher)

    if isinstance(publisher, str):
        publisher = re.split(r'\s*[-\/,]\s*', publisher)

    if publisher:
        for p in publisher:
            if p:
                created_publisher = Publisher.get_or_create(
                    name=p,
                    acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    user=user,
                    location=None,
                    official=None,
                    is_official=None,
                    url=None,
                    institution_type=None,
                )
                publisher_history = PublisherHistory.get_or_create(
                    institution=created_publisher,
                    user=user,
                )
                publisher_history.journal = journal
                publisher_history.save()
                created_owner = Owner.get_or_create(
                    name=p,
                    acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    user=user,
                    location=None,
                    official=None,
                    is_official=None,
                    url=None,
                    institution_type=None,
                )
                owner_history = OwnerHistory.get_or_create(
                    institution=created_owner,
                    user=user,
                )
                owner_history.journal = journal
                owner_history.save()
                journal.contact_name = p

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
    journal.submission_online_url = extract_value(url_of_submission_online)
    license_type = extract_value(license_of_use)
    if license_type:
        license = License.create_or_update(license_type=license_type, user=user)
        journal.use_license = license
    url_of_the_main_collection = extract_value(url_of_the_main_collection)
    assign_journal_to_main_collection(journal=journal, url_of_the_main_collection=url_of_the_main_collection)

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
        except (ValueError, TypeError):
            creation_date = None
        try:
            update_date = datetime.strptime(extract_value(update_date), "%Y%m%d")
        except (ValueError, TypeError):
            update_date = None

        if isinstance(notes, str):
            notes = [notes]
        n = "\n".join(notes)
        try:
            obj = Annotation.create_or_update(
                journal=journal,
                notes=n,
                creation_date=creation_date,
                update_date=update_date,
                user=user,
            )
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "function": "journal.sources.article_meta.update_panel_notes",
                    "journal_id": journal.id,
                    "notes": n,
                    "creation_date": f"{creation_date}",
                    "update_date": f"{update_date}",
                },
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
    journal.center_code = extract_value(center_code)
    journal.identification_number = extract_value(identification_number)
    journal.subtitle = extract_value(subtitle)
    journal.section = extract_value(section)
    journal.has_supplement = extract_value(has_supplement)
    journal.is_supplement = extract_value(is_supplement)
    journal.acronym_letters = extract_value(acronym_letters)
    set_ftp(journal, extract_value(ftp))
    set_user_subscription(journal, extract_value(user_subscription))

def set_ftp(journal, ftp):
    accept_ftp_strings = ('art', 'na', 'iss')
    if ftp and ftp.lower() in accept_ftp_strings:
        journal.ftp = ftp

def set_user_subscription(journal, user_subs):
    accept_user_subscription_string = ('sub', 'reg', 'na')
    if user_subs and user_subs.lower() in accept_user_subscription_string:
        journal.user_subscription = user_subs


def get_issns_from_scielo_journal(issn_scielo, title, issn_print, issn_electronic):
    if bool(issn_print) ^ bool(issn_electronic):
        # caso um dos ISSN esteja ausente, tenta recuperar o ISSN ausente de
        # um OfficialJournal anteriormente cadastrado se aplicável (#573)
        try:
            sj = SciELOJournal.objects.get(
                journal__title=title,
                issn_scielo=issn_scielo,
            )
            official_journal = sj.journal.official
            issn_print = issn_print or official_journal.issn_print
            issn_electronic = issn_electronic or official_journal.issn_electronic
        except (
            SciELOJournal.DoesNotExist,
            SciELOJournal.MultipleObjectsReturned,
        ):
            pass
    return issn_print, issn_electronic


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
):
    """
    Ex type_issn:
        [{"_": "ONLIN"}]
    Ex current_issn:
        [{"_": "1676-5648"}]
    Ex old_title:
        Ex 1: [{'_': 'Pesquisa Agropecuária Brasileira. Série Agronômica'}, {'_': 'Pesquisa Agropecuária Brasileira. Série Veterinária'}, {'_': 'Pesquisa Agropecuária Brasileira. Série Zootecnia'}]
        Ex 2: [{'_': 'Informe Epidemiológico do SUS'}]
    """
    title = extract_value(title)
    issn_scielo = extract_value(issn_scielo)

    issn_print, issn_electronic = get_issns(
        issn_print_or_electronic,
        issn_scielo,
        type_issn,
        current_issn,
    )
    issn_print, issn_electronic = get_issns_from_scielo_journal(
        issn_scielo, title, issn_print, issn_electronic)

    official_journal = OfficialJournal.create_or_update(
        user=user,
        issn_print=issn_print,
        issn_electronic=issn_electronic,
        issnl=None,
        title=title,
        issn_print_is_active=bool(issn_print),
    )

    get_or_update_parallel_titles(
        of_journal=official_journal, parallel_titles=parallel_titles
    )
    if new_title or old_title:
        official_journal.add_new_title(user, extract_value(new_title))
        official_journal.add_old_title(user, extract_value(old_title))
    official_journal.iso_short_title = extract_value(iso_short_title)
    official_journal.previous_journal_titles = extract_value(old_title)
    official_journal.next_journal_title = extract_value(new_title)

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
    """
    Ex sponsor:
        Ex 1: ['CNPq', 'FAPEMIG', 'UFMG', 'CAPES', 'Escola de Música da UFMG']
        Ex 2: MCT, FINEP, CNPq
        Ex 3: Conselho Nacional de Desenvolvimento Científico e Tecnológico
        Ex 4: MCT/CNPq/ FINEP
    """
    sponsor = extract_value(sponsor)
    if isinstance(sponsor, str):
        sponsor = re.split(r'\s*[-\/,]\s*', sponsor)
    if sponsor:
        for s in sponsor:
            ## FIXME
            ## Sponso de diferentes formas (insta_name e insta_acronym)
            ## Ex:
            ## CNPq
            ## Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira
            ## Fundação Getulio Vargas/ Escola de Administração de Empresas de São Paulo
            ## CNPq - Conselho Nacional de Desenvolvimento Científico e Tecnológico (PIEB)
            if s:
                created_sponsor = Sponsor.get_or_create(
                    name=s,
                    acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    user=user,
                    location=None,
                    official=None,
                    is_official=None,
                    url=None,
                    institution_type=None,
                )
                sponsor_history = SponsorHistory.get_or_create(
                    institution=created_sponsor,
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
                    try:
                        obj, created = SubjectDescriptor.objects.get_or_create(
                            value=word,
                            creator=user,
                        )
                        data.append(obj)
                    except Exception as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        UnexpectedEvent.create(
                            exception=e,
                            exc_traceback=exc_traceback,
                            detail={
                                "function": "journal.sources.am_to_core.get_or_create_subject_descriptor",
                                "journal_id": journal.id,
                                "subject": s,
                            },
                        )                        
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
                    value__iexact=value,
                )
                data.append(obj)
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
        journal.wos_area.set(data)


def get_or_create_indexed_at(journal, indexed_at, user):
    """
    indexed_at:
        [{'_': 'Index to Dental Literature'}, {'_': 'LILACS'}, {'_': 'Base de Dados BBO'}, {'_': "Ulrich's"}, {'_': 'Biological Abstracts'}, {'_': 'Medline'}]
    """
    data_index = []
    data_additional_indexed= []
    if indexed_at:
        indexed = extract_value(indexed_at)
        if isinstance(indexed, str):
            indexed = [indexed]
        for i in indexed:
            try:
                obj_index = IndexedAt.objects.get(Q(name__iexact=i) | Q(acronym__iexact=i))
                data_index.append(obj_index)
            except IndexedAt.DoesNotExist:
                try:
                    obj_additional_index = AdditionalIndexedAt.get_or_create(
                        name=i,
                        user=user,
                    )
                except Exception as e:
                    # Nao registra error caso valor de i seja None
                    continue
                data_additional_indexed.append(obj_additional_index)
        journal.indexed_at.set(data_index)
        journal.additional_indexed_at.set(data_additional_indexed)

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

    country = standardize_location(extract_value(publisher_city), Country, user=user)
    city = standardize_location(extract_value(publisher_city), City, user=user)
    state = standardize_location(extract_value(publisher_state), State, user=user)

    try:
        location = Location.create_or_update(
            user=user,
            country=country,
            state=state,
            city=city,
        )
    except Exception as e:
        location = None
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "journal.sources.article_meta.create_or_update_location",
                "journal_id": journal.id,
            },
        )          
    journal.contact_location = location

    address = extract_value(address)
    if address:
        if isinstance(address, str):
            address = [address]
        address = "\n".join(address)

    journal.contact_address = address

    return location


def standardize_location(value_location, ObjectLocation, user):
    standardized_value = None
    for item in ObjectLocation.standardize(value_location, user):
        standardized_value = next(iter(item.values()))
        if standardized_value:
            break
    return standardized_value


def get_or_update_parallel_titles(of_journal, parallel_titles):
    if parallel_titles:
        titles = extract_value(parallel_titles)
        if isinstance(titles, str):
            titles = [titles]
        for title in titles:
            JournalParallelTitle.create_or_update(
                official_journal=of_journal,
                text=title,
            )


def get_or_create_journal_history(scielo_journal, journal_history):
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
    if isinstance(copyright_holder_name, str):
        copyright_holder_name = [copyright_holder_name]

    if copyright_holder_name:
        for cp in copyright_holder_name:
            try:
                copyright_holder = CopyrightHolder.get_or_create(
                    name=cp,
                    acronym=None,
                    level_1=None,
                    level_2=None,
                    level_3=None,
                    user=user,
                    location=None,
                    official=None,
                    is_official=None,
                    url=None,
                    institution_type=None,
                )
                copyright_holder_history = CopyrightHolderHistory.get_or_create(
                    institution=copyright_holder,
                    user=user,
                )
                copyright_holder_history.journal = journal
                copyright_holder_history.save()
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "function": "journal.sources.am_to_core.assign_journal_to_main_collection",
                        "journal_id": journal.id,
                        "copyright_holder_name": copyright_holder_name
                    },
                )


def update_title_in_database(user, journal, code, acronym, title=None):
    code = extract_value(code)
    indexed_at = IndexedAt.objects.get(acronym__iexact=acronym)
    if not title:
        title = journal.title
    else:
        title = extract_value(title)    
    create_or_update_title_in_database(user=user, journal=journal, indexed_at=indexed_at, identifier=code, title=title)

def create_or_update_title_in_database(user, journal, indexed_at, title, identifier):
    TitleInDatabase.create_or_update(user=user, journal=journal, indexed_at=indexed_at, title=title, identifier=identifier)

def assign_journal_to_main_collection(journal, url_of_the_main_collection):
    if url_of_the_main_collection:
        try:
            cleaned_domain_query = url_of_the_main_collection.replace("http://", "").replace("https://", "") 
            collection = Collection.objects.get(domain=cleaned_domain_query)
            journal.main_collection = collection
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "function": "journal.sources.am_to_core.assign_journal_to_main_collection",
                    "journal_id": journal.id,
                    "cleaned_domain_query": cleaned_domain_query
                },
            )