from article import tasks


def run(username):
    tasks.remove_duplicate_articles_task.apply_async(kwargs=dict(username=username))
