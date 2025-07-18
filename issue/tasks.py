from datetime import datetime

import logging
import sys

from django.contrib.auth import get_user_model
from django.db.models import Q

from config import celery_app
from core.utils.utils import _get_user
from issue import controller
from issue.models import Issue
from issue.sources.article_meta import process_issue_article_meta
from tracker.models import UnexpectedEvent


User = get_user_model()

logger = logging.getLogger(__name__)


@celery_app.task()
def load_issue(*args):
    """
    Load issue record.

    Sync or Async function
    """

    user = User.objects.get(id=args[0] if args else 1)

    controller.load(user)


@celery_app.task()
def load_issue_from_article_meta(**kwargs):
    user = User.objects.get(id=kwargs["user_id"] if kwargs["user_id"] else 1)
    process_issue_article_meta(
        collection=kwargs["collection"], limit=kwargs["limit"], user=user
    )


@celery_app.task(bind=True, name="task_export_issues_to_articlemeta")
def task_export_issues_to_articlemeta(
    self,
    collections=[],
    issn=None,
    volume=None,
    number=None,
    force_update=True,
    user_id=None,
    username=None,
):
    """
    Export issues to ArticleMeta Database with flexible filtering.
    
    Args:
        collections: List of collections to export
        issn: Filter by ISSN
        volume: Filter by volume number
        issue: Filter by issue number
        force_update: Force update existing records
        user_id: User ID for authentication
        username: Username for authentication
    """
    user = _get_user(request=self.request, user_id=user_id, username=username)

    return controller.bulk_export_issues_to_articlemeta(
        collections=collections,
        issn=issn,
        volume=volume,
        number=number,
        force_update=force_update,
        user=user,
    )


@celery_app.task(bind=True, name="task_export_issue_to_articlemeta")
def task_export_issue_to_articlemeta(self, issue_code=None, force_update=True, user_id=None, username=None):
    """
    Export a specific issue to ArticleMeta Database.

    Args:
        issue_code: The primary key of the issue to export
        force_update: Force update existing records
        user_id: User ID for authentication
        username: Username for authentication
    """
    user =  _get_user(request=self.request, user_id=user_id, username=username)

    return controller.export_issue_to_articlemeta(
        issue_code=issue_code,
        force_update=force_update,
        user=user,
    )
