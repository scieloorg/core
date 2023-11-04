import logging
import sys
from datetime import datetime

from django.contrib.auth import get_user_model

from collection.models import Collection
from config import celery_app
from journal.sources import classic_website
from journal.sources.article_meta import process_journal_article_meta
from tracker.models import UnexpectedEvent

# from django.utils.translation import gettext as _


User = get_user_model()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


@celery_app.task(bind=True)
def load_journal_from_classic_website(self, username=None, user_id=None):
    user = _get_user(self.request, username=username, user_id=user_id)
    classic_website.load(user)




@celery_app.task(bind=True)
def load_journal_from_article_meta(self, username=None, user_id=None, limit=None):
    try:
        for item in Collection.objects.filter(collection_type="journals").iterator():
            load_journal_from_article_meta_for_one_collection.apply_async(
                kwargs=dict(
                    user_id=user_id,
                    username=username,
                    collection_acron=item.acron3,
                    limit=limit,
                )
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            e=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "journal.tasks.load_journal_from_article_meta",
            },
        )


@celery_app.task(bind=True)
def load_journal_from_article_meta_for_one_collection(
    self, username=None, user_id=None, collection_acron=None, limit=None
):
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        process_journal_article_meta(
            collection=collection_acron, limit=limit, user=user
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            e=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "journal.tasks.load_journal_from_article_meta_for_one_collection",
                "collection_acron": collection_acron,
            },
        )
