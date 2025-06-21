from collections import defaultdict

from core.utils.articlemeta_dict_utils import add_items, add_to_result
from journal.choices import STATUS
from journal.models import SciELOJournal, TitleInDatabase


def get_articlemeta_format_title(obj):
    result = defaultdict(list)
    scielo_journal = SciELOJournal.objects.filter(
        journal=obj, collection__is_active=True
    ).first()
    publisher_history = obj.publisher_history.all()

    add_to_result(
        "collection",
        (
            scielo_journal.collection.acron3
            if scielo_journal and scielo_journal.collection
            else None
        ), result
    )
    add_to_result("v5", obj.type_of_literature, result)
    add_to_result("v6", obj.treatment_level, result)
    add_to_result("v10", obj.center_code, result)
    add_to_result("v20", obj.national_code, result)
    add_to_result("v30", obj.identification_number, result)

    secs_code = TitleInDatabase.objects.filter(
        journal=obj, indexed_at__acronym__iexact="secs"
    )
    add_items("v37", [sc.identifier for sc in secs_code if sc.identifier], result)
    add_to_result(
        "v50", scielo_journal.status.lower() if scielo_journal.status else None, result
    )
    add_items(
        "v62", [ch.get_institution_name for ch in obj.copyright_holder_history.all()], result
    )
    add_to_result("v66", obj.ftp, result)
    add_to_result("v67", obj.user_subscription, result)
    add_to_result(
        "v68",
        (
            scielo_journal.journal_acron
            if scielo_journal and scielo_journal.journal_acron
            else None
        ), result
    )
    add_to_result("v69", obj.journal_url, result)
    if obj.vocabulary:
        add_to_result("v85", obj.vocabulary.acronym, result)
    add_to_result("v110", obj.subtitle, result)
    add_to_result(
        "v117", obj.standard.code if obj.standard and obj.standard.code else None, result
    )
    add_to_result("v130", obj.section, result)
    add_items(
        "v140", [sponsor.get_institution_name for sponsor in obj.sponsor_history.all()], result
    )
    add_to_result("v150", obj.short_title, result)
    add_to_result("v240", [other_title.title for other_title in obj.other_titles.all()], result)

    # Data of the object official
    if obj.official:
        add_to_result("v100", obj.title if obj.official.title else None, result)
        add_to_result(
            "v151",
            obj.official.iso_short_title if obj.official.iso_short_title else None,
            result
        )
        add_items("v230", [pt.text for pt in obj.official.parallel_titles if pt.text], result)
        add_to_result(
            "v301", obj.official.initial_year if obj.official.initial_year else None, result
        )
        add_to_result(
            "v302", obj.official.initial_volume if obj.official.initial_volume else None, result
        )
        add_to_result(
            "v303", obj.official.initial_number if obj.official.initial_number else None, result
        )

        year = obj.official.terminate_year
        month = obj.official.terminate_month

        if year and month:
            add_to_result("v304", year + month, result)
        elif year:
            add_to_result("v304", year, result)
        add_to_result(
            "v305", obj.official.final_volume if obj.official.final_volume else None, result
        )
        add_to_result(
            "v306",
            (
                obj.official.final_number
                if obj.official and obj.official.final_number
                else None
            ), result
        )

        issns = []
        if obj.official.issn_print:
            issns.append({"_": obj.official.issn_print, "t": "PRINT"})
        if obj.official.issn_electronic:
            issns.append({"_": obj.official.issn_electronic, "t": "ONLIN"})
        result["435"] = issns

        if obj.official.old_title.all():
            add_items(
                "v610", [old_title.title for old_title in obj.official.old_title.all()], result
            )
        if obj.official.new_title:
            add_to_result("v710", obj.official.new_title.title, result)

    if publisher_history:
        add_items(
            "v310",
            [publisher.get_institution_country_name for publisher in publisher_history],
            result
        )
        add_items(
            "v320",
            [publisher.get_instition_state_acronym for publisher in publisher_history],
            result
        )
        add_items(
            "v480", [publisher.get_institution_name for publisher in publisher_history],
            result
        )
        add_items(
            "v490",
            [publisher.get_institution_city_name for publisher in publisher_history],
            result
        )

    add_to_result(
        "v330", obj.level_of_publication if obj.level_of_publication else None, result
    )
    add_to_result("v340", obj.alphabet if obj.alphabet else None, result)
    add_items("v350", [lang.code2 for lang in obj.text_language.all()], result)
    add_items("v360", [lang.code2 for lang in obj.abstract_language.all()], result)
    add_to_result("v380", obj.frequency if obj.frequency else None, result)

    medline_titles = TitleInDatabase.objects.filter(
        journal=obj, indexed_at__acronym__iexact="medline"
    )
    add_items("v420", [medline.identifier for medline in medline_titles], result)
    add_items("v421", [medline.title for medline in medline_titles], result)
    add_to_result("v430", obj.classification, result)

    add_items("v440", [descriptor.value for descriptor in obj.subject_descriptor.all()], result)
    add_items("v441", [subject.value for subject in obj.subject.all()], result)
    add_items("v450", [index.name for index in obj.indexed_at.all()], result)

    add_to_result("v550", obj.has_supplement, result)
    add_to_result("v560", obj.is_supplement, result)

    add_items("v900", [annotation.notes for annotation in obj.annotation.all()], result)
    result["v901"] = (
        [
            {"l": mission.language.code2, "_": mission.get_text_pure}
            for mission in obj.mission.all()
            if mission.language and mission.get_text_pure
        ]
        if obj.mission
        else None
    )

    add_to_result("v940", obj.created, result)
    add_to_result("v941", obj.updated, result)

    return result


def collection_acron(scielo_journal, result):
    add_to_result(
        "collection",
        (
            scielo_journal.collection.acron3
            if scielo_journal and scielo_journal.collection
            else None
        ), result
    )

def title_medline(obj):
    """
    Title in Medline
    """
    medline_titles = TitleInDatabase.objects.filter(
        journal=obj, indexed_at__acronym__iexact="medline"
    )
    medline_titles



def type_of_literature(obj, result):
    add_to_result("v5", obj.type_of_literature, result)

def treatment_level(obj, result):
    add_to_result("v6", obj.treatment_level, result)

def center_code(obj, result):
    add_to_result("v10", obj.center_code, result)

def national_code(obj, result):
    add_to_result("v20", obj.national_code, result)

def registration_identification_number(obj, result):
    add_to_result("v30", obj.identification_number, result)

# TODO
# def type_of_issn(obj, result):
#     "v35"

def identification_code(obj, result):
    """
    Identification SECS
    """
    secs_code = TitleInDatabase.objects.filter(
        journal=obj, indexed_at__acronym__iexact="secs"
    )
    add_items("v37", [sc.identifier for sc in secs_code if sc.identifier], result)

def status_of_publication(scielo_journal, obj, result):
    add_to_result("v50", scielo_journal.status.lower() if scielo_journal.status else None, result)

def copyright(obj, result):
    add_items("v62", [ch.get_institution_name for ch in obj.copyright_holder_history.all()], result)

# TODO
# def address_of_editor(obj, result):
#     "v63"

def email(obj, result):
    add_items("v64", [e.email for e in obj.journal_email.all()], result)

# TODO
# def separate_html(obj, result):
#     "v65"

def ftp(obj, result):
    add_to_result("v66", obj.ftp, result)

def user_subscription(obj, result):
    add_to_result("v67", obj.user_subscription, result)

def journal_acron(scielo_journal, obj, result):
    """
    Publication identifier - acronym
    """
    add_to_result(
        "v68",
        (
            scielo_journal.journal_acron
            if scielo_journal and scielo_journal.journal_acron
            else None
        ), result
    )

def journal_url(obj, result):
    """
    External website address
    """
    add_to_result("v69", obj.journal_url, result)

def normalized_descriptor(obj, result):
    add_to_result("v85", obj.vocabulary, result)


def title_of_publication(obj, result):
    if obj.official:
        add_to_result("v100", obj.official.title, result)

def subtitle_of_publication(obj, result):
    add_to_result("v110", obj.subtitle, result)

def use_standard(obj, result):
    add_to_result("v117", obj.standard, result)

def title_of_section(obj, result):
    add_to_result("v130", obj.section, result)

def sponsor(obj, result):
    add_items("v140", [sponsor.get_institution_name for sponsor in obj.sponsor_history.all()], result)

def short_title(obj, result):
    add_to_result("v150", obj.short_title, result)


def short_title_lilacs(obj, result):
    add_to_result("v151", [medline.title for medline in title_medline(obj)], result)

def parallel_title(obj, result):
    if obj.official:
        add_items("v230", [pt.text for pt in obj.official.parallel_titles if pt.text], result)

def other_title(obj, result):
    add_to_result("v240", [other_title.title for other_title in obj.other_titles.all()], result)

def initial_year(obj, result):
    if obj.official:
        add_to_result("v301", obj.official.initial_year, result)
    
def initial_volume(obj, result):
    if obj.official:
        add_to_result("v302", obj.official.initial_volume, result)

def initial_number(obj, result):
    if obj.official:
        add_to_result("v303", obj.official.initial_number, result)

def terminate_year(obj, result):
    if obj.official:
        year = obj.official.terminate_year
        month = obj.official.terminate_month

        if year and month:
            add_to_result("v304", year + month, result)
        elif year:
            add_to_result("v304", year, result)

def terminate_volume(obj, result):
    if obj.official:
        add_to_result("v305", obj.official.terminate_volume, result)

def terminate_number(obj, result):
    if obj.official:
        add_to_result("v306", obj.official.final_number, result)

def publisher_country(publisher_history, result):
    add_items(
        "v310",
        [publisher.get_institution_country_name for publisher in publisher_history],
        result
    )

def publisher_state(publisher_history, result):
    add_items(
        "v320",
        [publisher.get_instition_state_acronym for publisher in publisher_history],
        result
    )

def level_of_publication(obj, result):
    add_to_result("v330", obj.level_of_publication, result)

def alphabet(obj, result):
    add_to_result("v340", obj.alphabet, result)

def text_language(obj, result):
    add_items("v350", [lang.code2 for lang in obj.text_language.all()], result)

def abstract_language(obj, result):
    add_items("v360", [lang.code2 for lang in obj.abstract_language.all()], result)

def frequency(obj, result):
    add_to_result("v380", obj.frequency, result)

def issn(scielo_journal, obj, result):
    add_to_result("v400", scielo_journal.issn_scielo, result)

def medline_code(obj, result):
    add_to_result("v420", [medline.identifier for medline in title_medline(obj)], result)

def medline_title(obj, result):
    add_to_result("v421", [medline.title for medline in title_medline(obj)], result)

def classification(obj, result):
    add_to_result("v430", obj.classification, result)

def subject_descriptor(obj, result):
    add_to_result("v440", [descriptor.value for descriptor in obj.subject_descriptor.all()], result)

def subject(obj, result):
    add_to_result("v441", [subject.value for subject in obj.subject.all()], result)

def indexed_at(obj, result):
    add_to_result("v450", [index.name for index in obj.indexed_at.all()], result)

def publisher_name(publisher_history, result):
    add_items(
        "v480",
        [publisher.get_institution_name for publisher in publisher_history],
        result
    )

def publisher_city(publisher_history, result):
    add_items(
        "v490",
        [publisher.get_institution_city_name for publisher in publisher_history],
        result
    )

def has_supplement(obj, result):
    add_to_result("v550", obj.has_supplement, result)

def is_supplement(obj, result):
    add_to_result("v560", obj.is_supplement, result)

def old_title(obj, result):
    if obj.official and obj.official.old_title:
        add_items("v610", [old_title.title for old_title in obj.official.old_title.all()], result)

def new_title(obj, result):
    if obj.official and obj.official.new_title:
        add_to_result("v710", obj.official.new_title.title, result)

def notes(obj, result):
    add_items("v900", [annotation.notes for annotation in obj.annotation.all()], result)

def mission(obj, result):
    result["v901"] = (
        [
            {"l": mission.language.code2, "_": mission.get_text_pure}
            for mission in obj.mission.all()
            if mission.language and mission.get_text_pure
        ]
        if obj.mission
        else None
    )

def created(obj, result):
    add_to_result("v940", obj.created, result)

def updated(obj, result):
    add_to_result("v941", obj.updated, result)