# tasks.py
import logging
import sys
from datetime import datetime

from django.contrib.auth import get_user_model

from config import celery_app
from .models import UnexpectedEvent, Hello


User = get_user_model()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


@celery_app.task(bind=True, name="cleanup_unexpected_events")
def delete_unexpected_events(self, exception_type, start_date=None, end_date=None, user_id=None, username=None):
    """
    Delete UnexpectedEvent records based on exception type and optional date range.
    """

    if exception_type == '__all__':
        UnexpectedEvent.objects.all().delete()
        return

    filters = {'exception_type__icontains': exception_type}
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
