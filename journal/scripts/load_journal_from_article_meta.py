from journal import tasks


def run(username):
    tasks.load_journal_from_article_meta.apply_async(
        kwargs={
            "username": username,
        }
    )
