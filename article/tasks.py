from django.contrib.auth import get_user_model

from config import celery_app

from . import controller

User = get_user_model()


@celery_app.task()
def load_funding_data(user, file_path):
    user = User.objects.get(pk=user)

    controller.read_file(user, file_path)
