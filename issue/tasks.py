from django.contrib.auth import get_user_model

from config import celery_app

from issue import controller


User = get_user_model()


@celery_app.task()
def load_issue(*args):
    """
    Load issue record.

    Sync or Async function
    """

    user = User.objects.get(id=args[0] if args else 1)

    controller.load(user)
