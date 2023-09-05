from journal import tasks


def run(user_id=None, collection="scl", offset=0, limit=10):
    tasks.load_journal_from_article_meta.apply_async(
        kwargs={
            "collection": collection,
            "limit": limit,
            "user_id": user_id,
        }
    )
