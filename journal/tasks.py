import logging
import sys
from datetime import datetime

from django.contrib.auth import get_user_model

from collection.models import Collection
from config import celery_app
from core.utils.utils import fetch_data
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


@celery_app.task(bin=True)
def load_journal_from_classic_website(self, username=None, user_id=None):
    user = _get_user(self.request, username=username, user_id=user_id)
    classic_website.load(user)


@celery_app.task(bin=True)
def load_journal_from_article_meta(self, username=None, user_id=None):
    user = _get_user(self.request, username=username, user_id=user_id)
    process_journal_article_meta(
        collection=kwargs["collection"], limit=kwargs["limit"], user=user
    )
