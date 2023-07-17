from issue import tasks


def run():
    tasks.load_issue_from_article_meta.apply_async()