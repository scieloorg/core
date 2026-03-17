# tasks.py
import logging
import sys
from datetime import datetime

from config import celery_app
from .models import UnexpectedEvent, Hello


@celery_app.task(bind=True, name="cleanup_unexpected_events")
def delete_unexpected_events(self, exception_type, start_date=None, end_date=None):
    """
    Delete UnexpectedEvent records based on exception type and optional date range.
    """

    filters = {}
    if exception_type:
        filters['exception_type__icontains'] =  exception_type

    if start_date:
        start_date = datetime.fromisoformat(start_date)
        filters['created__gte'] = start_date
    if end_date:
        end_date = datetime.fromisoformat(end_date)
        filters['created__lte'] = end_date

    UnexpectedEvent.objects.filter(**filters).delete()


@celery_app.task(bind=True)
def hello(self, user_id=None):
    """
    Register Hello records
    """
    try:
        logging.info("Hello!")
        Hello.create()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        Hello.create(
            exception=e,
            exc_traceback=exc_traceback,
        )
