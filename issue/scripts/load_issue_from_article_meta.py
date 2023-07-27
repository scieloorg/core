from issue import tasks


def run(user_id=None, collection="scl", offset=0, limit=100):
    tasks.load_issue_from_article_meta.apply_async(
        kwargs={
            "collection": collection,
            "limit": limit,
            "user_id": user_id,
        }
    )
