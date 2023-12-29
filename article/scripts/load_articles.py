from article.tasks import load_articles


def run(username=None):
    load_articles.apply_async(
        kwargs={
            "username": username
        }
    )
