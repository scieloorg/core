from collections import defaultdict

from journal.models import SciELOJournal, TitleInDatabase
from journal.choices import STATUS
from core.utils.articlemeta_dict_utils import add_to_result, add_items

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
