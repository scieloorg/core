from core.utils import utils
from core.utils.rename_dictionary_keys import rename_dictionary_keys
from journal.utils.correspondencia import correspondencia_journal
from journal.utils.journal_utils import create_or_update_scielo_journal
from core.utils.rename_dictionary_keys import rename_dictionary_keys
from journal.utils.request_api_article_meta import request_journal_article_meta
from journal.exceptions import (
    OfficialJournalCreateOrUpdateError,
    SciELOJournalCreateOrUpdateError,
)

class SciELOJournalArticleMetaCreateUpdateEror(Exception):
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
            journal_dict = rename_dictionary_keys(
                data_journal, correspondencia_journal
            )

            try:
                create_or_update_scielo_journal(
                    title=journal_dict.get("publication_title"),
                    issn_scielo=journal_dict.get("issn_id"),
                    short_title=journal_dict.get("short_title"),
                    submission_online_url=journal_dict.get("url_of_submission_online"),
                    open_access=journal_dict.get("license_of_use"),
                    issn_print_or_electronic=journal_dict.get("issn_print_or_electronic"),
                    type_issn=journal_dict.get("type_issn"),
                    current_issn=journal_dict.get("current_issn"),
                    collection=journal_dict.get("collection"),
                    user=user,
                    journal_acron=journal_dict.get("acronym"),
                    )
            except SciELOJournalArticleMetaCreateUpdateEror as e:
                raise SciELOJournalArticleMetaCreateUpdateEror(e)

        offset += 10
        data = request_journal_article_meta(
            collection=collection, limit=limit, offset=offset
        )
