from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from collection.models import Collection
from config import celery_app

User = get_user_model()


def _get_user(user_id=None, username=None):
    if user_id:
        return User.objects.get(pk=user_id)
    if username:
        return User.objects.get(username=username)
    raise ValueError("user_id or username is required")


@celery_app.task(bind=True)
def task_load_collections(self, user_id=None, username=None):
    user = _get_user(user_id, username)
    Collection.load(user)


@celery_app.task(bind=True)
def task_complete_network_classification(self, user_id=None, username=None):
    """
    Preenche network_classification das coleções que estão sem esse dado
    """
    user = _get_user(user_id, username)
    return Collection.complete_network_classification(user)
