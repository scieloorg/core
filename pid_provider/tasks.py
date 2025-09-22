import os
import sys
import logging

from django.contrib.auth import get_user_model

from config import celery_app
from core.utils.profiling_tools import (
    profile_function,
)  # ajuste o import conforme sua estrutura
from pid_provider.provider import PidProvider
from tracker.models import UnexpectedEvent

# from django.utils.translation import gettext_lazy as _


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
def task_provide_pid_for_xml_zip(
    self,
    username=None,
    user_id=None,
    zip_filename=None,
):
    return _provide_pid_for_xml_zip(username, user_id, zip_filename)


@profile_function
def _provide_pid_for_xml_zip(
    username=None,
    user_id=None,
    zip_filename=None,
):
    try:
        user = _get_user(None, username=username, user_id=user_id)
        logging.info("Running task_provide_pid_for_xml_zip")
        pp = PidProvider()
        for response in pp.provide_pid_for_xml_zip(
            zip_filename,
            user,
            filename=None,
            origin_date=None,
            force_update=None,
            is_published=None,
            registered_in_core=None,
            caller="core",
        ):
            try:
                response.pop("xml_with_pre")
            except KeyError:
                pass
            return response
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "_provide_pid_for_xml_zip",
                "detail": dict(
                    username=username,
                    user_id=user_id,
                    zip_filename=zip_filename,
                ),
            },
        )
        return {
            "error_msg": f"Unable to provide pid for {zip_filename} {e}",
            "error_type": str(type(e)),
        }


@celery_app.task(bind=True)
def task_delete_provide_pid_tmp_zip(
    self,
    temp_file_path,
):
    if temp_file_path and os.path.exists(temp_file_path):
        os.remove(temp_file_path)
