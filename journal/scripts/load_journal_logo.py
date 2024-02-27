from journal import tasks


def run(username):
    tasks.load_journal_logo.apply_async(
        kwargs={
            "username": username,
            }
    )
