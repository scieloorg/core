from journal import tasks
from journal.utils.request_api_article_meta import request_journal_article_meta


def run(user_id=None, collection="scl", offset=0, limit=10):
    tasks.load_journal_from_article_meta.apply_async(
        kwargs={
            "collection": collection,
            "limit": limit,
            "user_id": user_id,
        }
    )
