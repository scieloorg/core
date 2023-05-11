from article.tasks import load_articles

def run():
    load_articles.apply_async()
    