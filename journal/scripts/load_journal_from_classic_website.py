from journal import tasks


def run(username):
    tasks.load_journal_from_classic_website.apply_async(kwargs=dict(username=username))
