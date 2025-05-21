from journal import tasks


def run(username, collection=None):
    tasks.load_journal_from_article_meta.apply_async(
        kwargs={"username": username, "collection_acron": collection, "load_data": True}
    )
