from journal import tasks


def run():
    tasks.assign_logo_to_all_journals.apply_async()
