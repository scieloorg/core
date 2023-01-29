from django.contrib.auth import get_user_model

from config import celery_app

from . import controller


User = get_user_model()


@celery_app.task()
def load_financial_data(*args):
    user = User.objects.get(id=args[0] if args else 1)

    controller.read_file(user)
