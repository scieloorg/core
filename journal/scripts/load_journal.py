from journal import tasks


def run():
    tasks.load_journal.apply_async()
