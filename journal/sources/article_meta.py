import sys

from core.utils.rename_dictionary_keys import rename_dictionary_keys
from core.utils.utils import fetch_data
from journal.utils import journal_utils
from journal.utils.correspondencia import correspondencia_journal
from tracker.models import UnexpectedEvent


class SciELOJournalArticleMetaCreateUpdateError(Exception):
    def __init__(self, message):
        super().__init__(f"Failed to save SciELO Journal from article meta: {message}")


def _get_collection_journals(offset=None, limit=None, collection=None):
    limit = limit or 10
    offset = f"&offset={offset}" if offset else ""
    if not collection:
        raise ValueError(
            "journal.sources.article_meta._get_collection_journals requires collection"
        )
    url = (
        f"https://articlemeta.scielo.org/api/v1/journal/identifiers/?collection={collection}&limit={limit}"
        + offset
    )
    data = fetch_data(url, json=True, timeout=30, verify=True)
    return data


def process_journal_article_meta(collection, limit, user):
    offset = 0
    data = _get_collection_journals(collection=collection, limit=limit)
    total_limit = data["meta"]["total"]
    while offset < total_limit:
        for journal in data["objects"]:
            issn = journal["code"]
            url_journal = f"https://articlemeta.scielo.org/api/v1/journal/?collection={collection}&issn={issn}"
            data_journal = fetch_data(url_journal, json=True, timeout=30, verify=True)
            _register_journal_data(user, collection, issn, data_journal)

        offset += 10
        data = _get_collection_journals(
            collection=collection, limit=limit, offset=offset
        )


def _register_journal_data(user, collection, issn, data_journal):
    try:
        journal_dict = rename_dictionary_keys(data_journal, correspondencia_journal)

        official_journal = journal_utils.create_or_update_official_journal(
            title=journal_dict.get("publication_title"),
            new_title=journal_dict.get("new_title"),
            old_title=journal_dict.get("old_title"),
            issn_print_or_electronic=journal_dict.get("issn_print_or_electronic"),
            issn_scielo=journal_dict.get("issn_id"),
            type_issn=journal_dict.get("type_issn"),
            current_issn=journal_dict.get("current_issn"),
            initial_date=journal_dict.get("initial_date"),
            terminate_date=journal_dict.get("terminate_date"),
            initial_volume=journal_dict.get("initial_volume"),
            initial_number=journal_dict.get("initial_number"),
            final_volume=journal_dict.get("final_volume"),
            final_number=journal_dict.get("final_number"),
            iso_short_title=journal_dict.get("iso_short_title"),
            parallel_titles=journal_dict.get("parallel_titles"),
            user=user,
        )
        journal = journal_utils.create_or_update_journal(
            official_journal=official_journal,
            title=journal_dict.get("publication_title"),
            short_title=journal_dict.get("short_title"),
            other_titles=journal_dict.get("other_titles"),
            submission_online_url=journal_dict.get("url_of_submission_online"),
            user=user,
        )
        journal_utils.create_or_update_scielo_journal(
            journal=journal,
            collection=journal_dict.get("collection"),
            issn_scielo=journal_dict.get("issn_id"),
            journal_acron=journal_dict.get("acronym"),
            status=journal_dict.get("publication_status"),
            journal_history=journal_dict.get(
                "journal_status_history_in_this_collection"
            ),
            user=user,
        )
        journal_utils.update_panel_scope_and_about(
            journal=journal,
            mission=journal_dict.get("mission"),
            sponsor=journal_dict.get("sponsor"),
            subject=journal_dict.get("study_area"),
            subject_descriptors=journal_dict.get("subject_descriptors"),
            wos_scie=journal_dict.get("science_citation_index_expanded"),
            wos_ssci=journal_dict.get("social_sciences_citation_index"),
            wos_ahci=journal_dict.get("arts_humanities_citation_index"),
            wos_areas=journal_dict.get("subject_categories"),
            user=user,
        )
        journal_utils.update_panel_interoperation(
            journal=journal,
            indexed_at=journal_dict.get("indexing_coverage"),
            secs_code=journal_dict.get("secs_code"),
            medline_code=journal_dict.get("medline_code"),
            medline_short_title=journal_dict.get("medline_short_title"),
            user=user,
        )
        journal_utils.update_panel_information(
            journal=journal,
            frequency=journal_dict.get("frequency"),
            publishing_model=journal_dict.get("publishing_model"),
            text_language=journal_dict.get("text_idiom"),
            abstract_language=journal_dict.get("abstract_language"),
            standard=journal_dict.get("standard"),
            alphabet=journal_dict.get("alphabet"),
            classification=journal_dict.get("classification"),
            type_of_literature=journal_dict.get("type_of_literature"),
            treatment_level=journal_dict.get("treatment_level"),
            level_of_publication=journal_dict.get("level_of_publication"),
            national_code=journal_dict.get("national_code"),
            vocabulary=journal_dict.get("controled_vocabulary"),
            user=user,
        )
        journal_utils.update_panel_institution(
            journal=journal,
            publisher=journal_dict.get("publisher"),
            copyright_holder=journal_dict.get("copyright_holder"),
            address=journal_dict.get("address"),
            electronic_address=journal_dict.get("electronic_address"),
            publisher_country=journal_dict.get("publisher_country"),
            publisher_state=journal_dict.get("publisher_state"),
            publisher_city=journal_dict.get("publisher_city"),
            user=user,
        )
        journal_utils.update_panel_website(
            journal=journal,
            url_of_the_journal=journal_dict.get("url_of_the_journal"),
            url_of_submission_online=journal_dict.get("url_of_submission_online"),
            url_of_the_main_collection=journal_dict.get("url_of_the_main_collection"),
            license_of_use=journal_dict.get("license_of_use"),
            user=user,
        )
        journal_utils.update_panel_notes(
            journal=journal,
            notes=journal_dict.get("notes"),
            creation_date=journal_dict.get("creation_date"),
            update_date=journal_dict.get("update_date"),
            user=user,
        )
        journal_utils.update_panel_legacy_compatibility_fields(
            journal=journal,
            center_code=journal_dict.get("center_code"),
            identification_number=journal_dict.get("identification_number"),
            ftp=journal_dict.get("ftp"),
            user_subscription=journal_dict.get("user_subscription"),
            subtitle=journal_dict.get("subtitle"),
            section=journal_dict.get("section"),
            has_supplement=journal_dict.get("has_supplement"),
            is_supplement=journal_dict.get("is_supplement"),
            acronym_letters=journal_dict.get("acronym_letters"),
        )
        journal.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            e=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "journal.sources.article_meta._register_journal_data",
                "collection": collection,
                "issn": issn,
                "data_journal": data_journal,
            },
        )
