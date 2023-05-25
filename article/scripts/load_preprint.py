from article.tasks import load_preprint


def run(user_id=None):
    load_preprint.apply_async(args=(user_id,))
