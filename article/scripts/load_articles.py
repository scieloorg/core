from article.tasks import load_articles


def run(user_id=None):
    load_articles.apply_async(args=(user_id,))
