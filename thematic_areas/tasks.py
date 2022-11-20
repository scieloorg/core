from django.contrib.auth import get_user_model

from config import celery_app

from thematic_areas import controller


User = get_user_model()


@celery_app.task()
def load_thematic_area(*args):
    """
    Load thematic area from CSV file.

    Sync or Async function
    """

    user = User.objects.get(id=args[0]) if args else 1

    controller.load_thematic_area(user)
