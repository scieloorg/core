from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from collection.models import Collection
from config import celery_app

User = get_user_model()


@celery_app.task(bind=True)
def task_load_collections(self, user_id=None, username=None):
    if user_id:
        user = User.objects.get(pk=user_id)
    elif username:
        user = User.objects.get(username=username)
    else:
        raise ValueError("user_id or username is required")
    Collection.load(user)
