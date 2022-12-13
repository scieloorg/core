from django.contrib.auth import get_user_model

from config import celery_app

from journal import controller


User = get_user_model()


@celery_app.task()
def load_journal(*args):
    """
    Load journal record.

    Sync or Async function
    """

    user = User.objects.get(id=args[0] if args else 1)

    controller.load(user)
