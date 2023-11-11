import logging

from django.contrib.auth import get_user_model

from collection.models import Collection
from config import celery_app
from core.models import Language
from journal.models import Standard, Subject, WebOfKnowledge
from location.models import City, Country, State

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
    Standard.load(user)
    Subject.load(user)
    WebOfKnowledge.load(user)
    City.load(user)
    State.load(user)
