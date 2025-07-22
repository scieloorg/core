import os
import sys
import logging

from django.contrib.auth import get_user_model

from collection.models import Collection
from config import celery_app
from core.utils.utils import fetch_data
from pid_provider.models import CollectionPidRequest, PidRequest
from pid_provider.provider import PidProvider
from pid_provider.sources import am
from pid_provider.sources.harvesting import provide_pid_for_opac_and_am_xml
from tracker.models import UnexpectedEvent

# from django.utils.translation import gettext as _


User = get_user_model()
pid_provider = PidProvider()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


def _load_collections(user):
    if Collection.objects.count() == 0:
        try:
            Collection.load(user)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "function": "_load_collections",
                },
            )
            raise


def _get_begin_date(user, collection_acron):
    try:
        obj = CollectionPidRequest.create_or_update(
            user=user,
            collection=Collection.objects.get(acron3=collection_acron),
        )
        return obj.end_date
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "_get_begin_date",
                "collection_acron": collection_acron,
            },
        )
    return None


@celery_app.task(bind=True, name="provide_pid_for_am_article")
def provide_pid_for_am_article(
    self,
    username=None,
    user_id=None,
    item=None,
    force_update=None,
):
    try:
        uri = None
        collection_acron = item["collection_acron"]
        pid_v2 = item["pid_v2"]
        origin_date = item["processing_date"]
        uri = (
            f"https://articlemeta.scielo.org/api/v1/article/?"
            f"collection={collection_acron}&code={pid_v2}&format=xmlrsps"
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "provide_pid_for_am_article",
                "uri": uri,
                "item": item,
            },
        )
    else:
        task_provide_pid_for_xml_uri.apply_async(
            kwargs={
                "uri": uri,
                "username": username,
                "user_id": user_id,
                "pid_v2": pid_v2,
                "pid_v3": None,
                "collection_acron": collection_acron,
                "journal_acron": None,
                "year": None,
                "origin_date": origin_date,
                "force_update": force_update,
            }
        )


@celery_app.task(bind=True, name="provide_pid_for_am_xmls")
def provide_pid_for_am_xmls(
    self,
    username=None,
    user_id=None,
    collections=None,
    force_update=None,
    limit=None,
    stop=None,
):

    user = _get_user(self.request, username=username, user_id=user_id)
    _load_collections(user)

    collections = collections or [
        "arg",
        "bol",
        "chl",
        "col",
        "cri",
        "cub",
        "ecu",
        "esp",
        "mex",
        "prt",
        "pry",
        "psi",
        "rve",
        "spa",
        "sza",
        "ury",
        "ven",
        "wid",
    ]
    for item in collections:
        from_date = _get_begin_date(user, item) or "1997-01-01"
        task_provide_pid_for_am_collection.apply_async(
            kwargs={
                "username": username,
                "user_id": user_id,
                "collection_acron": item,
                "from_date": from_date,
                "force_update": force_update,
                "limit": limit,
                "stop": stop,
            }
        )


@celery_app.task(bind=True, name="task_provide_pid_for_am_collection")
def task_provide_pid_for_am_collection(
    self,
    username=None,
    user_id=None,
    collection_acron=None,
    from_date=None,
    limit=None,
    force_update=None,
    stop=None,
):
    harvester = am.AMHarvesting(
        collection_acron=collection_acron, from_date=from_date, limit=limit, stop=stop
    )

    for uri in harvester.uris():
        try:
            # consulta AM para trazer identificadores
            response = fetch_data(uri, json=True, timeout=30, verify=True)

            # get_items retorna gerador, list() é para tornar "serializável"
            items = list(harvester.get_items(response))

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "task_provide_pid_for_am_collection",
                    "uri": uri,
                },
            )
        else:
            for item in items:
                provide_pid_for_am_article.apply_async(
                    kwargs={
                        "username": username,
                        "user_id": user_id,
                        "item": item,
                        "force_update": force_update,
                    }
                )


@celery_app.task(bind=True)
def retry_to_provide_pid_for_failed_uris(
    self,
    username=None,
    user_id=None,
):
    for item in PidRequest.items_to_retry():
        try:
            params = {
                "uri": item.origin,
                "username": username,
                "user_id": user_id,
                "origin_date": item.origin_date,
            }
            params.update(item.detail or {})
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "retry_to_provide_pid_for_failed_uris",
                    "item": str(item),
                    "detail": params,
                },
            )
        else:
            task_provide_pid_for_xml_uri.apply_async(kwargs=params)


@celery_app.task(bind=True)
def task_provide_pid_for_xml_uri(
    self,
    uri,
    username=None,
    user_id=None,
    pid_v2=None,
    pid_v3=None,
    collection_acron=None,
    journal_acron=None,
    year=None,
    origin_date=None,
    force_update=None,
):
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        provide_pid_for_opac_and_am_xml(
            user,
            uri,
            pid_v2=pid_v2,
            pid_v3=pid_v3,
            collection_acron=collection_acron,
            journal_acron=journal_acron,
            year=year,
            origin_date=origin_date,
            force_update=force_update,
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_provide_pid_for_xml_uri",
                "detail": dict(
                    pid_v2=pid_v2,
                    pid_v3=pid_v3,
                    collection_acron=collection_acron,
                    journal_acron=journal_acron,
                    year=year,
                    origin_date=origin_date,
                    force_update=force_update,
                ),
            },
        )


@celery_app.task(bind=True)
def task_provide_pid_for_xml_zip(
    self,
    username=None,
    user_id=None,
    zip_filename=None,
):
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        logging.info("Running task_provide_pid_for_xml_zip")
        response = pid_provider.provide_pid_for_xml_zip(
            zip_filename,
            user,
            filename=None,
            origin_date=None,
            force_update=None,
            is_published=None,
            registered_in_core=None,
            caller="core",
        )
        logging.info("fim Running task_provide_pid_for_xml_zip")
        try:
            response = list(response)[0]
        except IndexError:
            response = {}
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
                "task": "task_provide_pid_for_xml_zip",
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

