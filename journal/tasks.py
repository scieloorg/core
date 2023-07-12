from django.contrib.auth import get_user_model


from config import celery_app
from journal import controller
from journal.sources.article_meta import journal_article_meta

User = get_user_model()


@celery_app.task()
def load_journal(*args):
    """
    Load journal record.

    Sync or Async function
    """

    user = User.objects.get(id=args[0] if args else 1)

    controller.load(user)


@celery_app.task()
def load_journal_from_article_meta(**kwargs):
    user = User.objects.get(id=kwargs["user_id"] if kwargs["user_id"] else 1)
    journal_article_meta(
        collection=kwargs["collection"], limit=kwargs["limit"], user=user
    )
