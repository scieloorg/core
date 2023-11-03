from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from collection.models import Collection
from config import celery_app

User = get_user_model()


@celery_app.task(bind=True)
def task_load_collections(self, user_id=None, username=None):
    if user_id:
        user = User.objects.get(pk=user_id)
    if username:
        user = User.objects.get(username=username)
    Collection.load(user)
