import logging

from django.contrib.auth import get_user_model
from config import celery_app
from collection.models import Collection
from core.models import Language


User = get_user_model()


def _get_user(user_id, username):
    if user_id:
        return User.objects.get(pk=user_id)
    if username:
        return User.objects.get(username=username)


@celery_app.task(bind=True)
def task_start(
    self,
    user_id=None,
    username=None,
):
    user = _get_user(user_id, username)
    Language.load(user)
    Country.load(user)
    Collection.load(user)

