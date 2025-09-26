import logging
import sys
from datetime import datetime

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
def load_issue(user_id=None, username=None):
    """
    Load issue record.

    Sync or Async function
    """

    user = _get_user(request=None, user_id=user_id, username=username)

    controller.load(user)


@celery_app.task()
def load_issue_from_article_meta(
    user_id=None, username=None, collection=None, limit=None
):
    user = _get_user(request=None, user_id=user_id, username=username)
    if not isinstance(limit, int):
        limit = 100
    process_issue_article_meta(collection=collection, limit=limit, user=user)


@celery_app.task(bind=True, name="task_export_issues_to_articlemeta")
def task_export_issues_to_articlemeta(
    self,
    collection_acron_list=None,
    journal_acron_list=None,
    publication_year=None,
    volume=None,
    number=None,
    supplement=None,
    force_update=False,
    user_id=None,
    username=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
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
        user,
        collection_acron_list,
        journal_acron_list,
        publication_year,
        volume,
        number,
        supplement,
        from_date,
        until_date,
        days_to_go_back,
        force_update,
    )


@celery_app.task(bind=True, name="task_export_issue_to_articlemeta")
def task_export_issue_to_articlemeta(
    self,
    collection_acron,
    journal_acron,
    publication_year=None,
    volume=None,
    number=None,
    supplement=None,
    force_update=None,
    user_id=None,
    username=None,
):

    user = _get_user(request=self.request, user_id=user_id, username=username)

    return controller.bulk_export_issues_to_articlemeta(
        user,
        collection_acron_list=[collection_acron],
        journal_acron_list=[journal_acron],
        publication_year=publication_year,
        volume=volume,
        number=number,
        supplement=supplement,
        force_update=force_update,
    )
