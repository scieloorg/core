from journal import tasks


def run():
    tasks.update_journal_valid_field.apply_async()