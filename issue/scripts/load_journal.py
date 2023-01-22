from issue import tasks


def run():
    tasks.load_issue.apply_async()
