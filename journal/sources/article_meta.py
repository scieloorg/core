from core.utils import utils
from core.utils.rename_dictionary_keys import rename_dictionary_keys
from journal.utils.correspondencia import correspondencia_journal
from journal.utils import journal_utils
from core.utils.rename_dictionary_keys import rename_dictionary_keys
from journal.utils.request_api_article_meta import request_journal_article_meta


class SciELOJournalArticleMetaCreateUpdateError(Exception):
    def __init__(self, message):
        super().__init__(f"Failed to save SciELO Journal from article meta: {message}")


def process_journal_article_meta(collection, limit, user):
    offset = 0
    data = request_journal_article_meta(collection=collection, limit=limit)
    total_limit = data["meta"]["total"]
    while offset < total_limit:
        for journal in data["objects"]:
            issn = journal["code"]
            url_journal = f"https://articlemeta.scielo.org/api/v1/journal/?issn={issn}"
            data_journal = utils.fetch_data(
                url_journal, json=True, timeout=30, verify=True
            )
            journal_dict = rename_dictionary_keys(data_journal, correspondencia_journal)
            journal = journal_utils.create_or_update_journal(
                title=journal_dict.get("publication_title"),
                issn_scielo=journal_dict.get("issn_id"),
                short_title=journal_dict.get("short_title"),
                other_titles=journal_dict.get("other_titles"),
                submission_online_url=journal_dict.get("url_of_submission_online"),
                open_access=journal_dict.get("license_of_use"),
                issn_print_or_electronic=journal_dict.get("issn_print_or_electronic"),
                type_issn=journal_dict.get("type_issn"),
                current_issn=journal_dict.get("current_issn"),
                user=user,
            )
            journal_utils.create_or_update_scielo_journal(
                journal=journal,
                collection=journal_dict.get("collection"),
                issn_scielo=journal_dict.get("issn_id"),
                journal_acron=journal_dict.get("acronym"),
                user=user,
            )
            journal_utils.create_scope(
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
            journal_utils.create_interoperation(
                journal=journal,
                indexed_at=journal_dict.get("indexing_coverage"),
                secs_code=journal_dict.get("secs_code"),
                medline_code=journal_dict.get("medline_code"),
                medline_short_title=journal_dict.get("medline_short_title"),
                user=user,
            )
            journal_utils.create_information(
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
            journal.save()
        offset += 10
        data = request_journal_article_meta(
            collection=collection, limit=limit, offset=offset
        )
