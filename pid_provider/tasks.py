import logging
import sys
from datetime import datetime

from django.contrib.auth import get_user_model

from collection.models import Collection
from config import celery_app
from core.utils.utils import fetch_data
from pid_provider.models import CollectionPidRequest, PidRequest
from pid_provider.sources import am
from pid_provider.sources.harvesting import provide_pid_for_opac_and_am_xml
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


"""
{
    "begin_date":"2023-06-01 00-00-00",
    "collection":"scl",
    "dictionary_date": "Sat, 01 Jul 2023 00:00:00 GMT",
    "documents":{
        "JFhVphtq6czR6PHMvC4w38N": {
            "aop_pid":"",
            "create":"Sat, 28 Nov 2020 23:42:43 GMT",
            "default_language":"en",
            "journal_acronym":"aabc",
            "pid":"S0001-37652012000100017",
            "pid_v1":"S0001-3765(12)08400117",
            "pid_v2":"S0001-37652012000100017",
            "pid_v3":"JFhVphtq6czR6PHMvC4w38N",
            "publication_date":"2012-05-22",
            "update":"Fri, 30 Jun 2023 20:57:30 GMT"
        },
        "ZZYxjr9xbVHWmckYgDwBfTc":{
            "aop_pid":"",
            "create":"Sat, 28 Nov 2020 23:42:37 GMT",
            "default_language":"en",
            "journal_acronym":"aabc",
            "pid":"S0001-37652012000100014",
            "pid_v1":"S0001-3765(12)08400114",
            "pid_v2":"S0001-37652012000100014",
            "pid_v3":"ZZYxjr9xbVHWmckYgDwBfTc",
            "publication_date":"2012-02-24",
            "update":"Fri, 30 Jun 2023 20:56:59 GMT",
        }
    }
}
"""


@celery_app.task(bind=True, name="provide_pid_for_opac_article")
def provide_pid_for_opac_article(
    self,
    username=None,
    user_id=None,
    collection_acron=None,
    pid_v3=None,
    article=None,
    force_update=None,
):
    try:
        logging.info(article)
        acron = article["journal_acronym"]
        uri = f"https://www.scielo.br/j/{acron}/a/{pid_v3}/?format=xml"
        origin_date = datetime.strptime(
            article.get("update") or article.get("create"),
            "%a, %d %b %Y %H:%M:%S %Z",
        ).isoformat()[:10]
        year = article["publication_date"][:4]

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "provide_pid_for_opac_article",
                "pid_v3": pid_v3,
                "article": article,
            },
        )
    else:
        task_provide_pid_for_xml_uri.apply_async(
            kwargs={
                "uri": uri,
                "username": username,
                "user_id": user_id,
                "pid_v2": None,
                "pid_v3": pid_v3,
                "collection_acron": collection_acron,
                "journal_acron": acron,
                "year": year,
                "origin_date": origin_date,
                "force_update": force_update,
            }
        )


@celery_app.task(bind=True, name="provide_pid_for_opac_xmls")
def provide_pid_for_opac_xmls(
    self,
    username=None,
    user_id=None,
    begin_date=None,
    end_date=None,
    limit=None,
    pages=None,
    force_update=None,
):

    page = 1
    limit = limit or 100
    collection_acron = "scl"
    end_date = end_date or datetime.utcnow().isoformat()[:10]

    if not begin_date:
        user = _get_user(self.request, username=username, user_id=user_id)
        _load_collections(user)
        begin_date = _get_begin_date(user, collection_acron) or "2000-01-01"

    while True:
        try:
            uri = (
                f"https://www.scielo.br/api/v1/counter_dict?end_date={end_date}"
                f"&begin_date={begin_date}&limit={limit}&page={page}"
            )
            response = fetch_data(uri, json=True, timeout=30, verify=True)
            pages = pages or response["pages"]
            documents = response["documents"]

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "provide_pid_for_opac_xmls",
                    "uri": uri,
                },
            )

        else:
            for pid_v3, article in documents.items():
                try:
                    provide_pid_for_opac_article.apply_async(
                        kwargs={
                            "username": username,
                            "user_id": user_id,
                            "collection_acron": collection_acron,
                            "pid_v3": pid_v3,
                            "article": article,
                            "force_update": force_update,
                        }
                    )
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "task": "provide_pid_for_opac_xmls",
                            "pid_v3": pid_v3,
                            "article": article,
                        },
                    )

        finally:
            page += 1
            if page > pages:
                break


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
            origin_date = item.origin_date
            uri = item.origin

            if item.detail:
                pid_v2 = item.detail.get("pid_v2")
                pid_v3 = item.detail.get("pid_v3")
                collection_acron = item.detail.get("collection_acron")
                journal_acron = item.detail.get("journal_acron")
                year = item.detail.get("year")
            else:
                pid_v2 = None
                pid_v3 = None
                collection_acron = None
                journal_acron = None
                year = None
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "retry_to_provide_pid_for_failed_uris",
                    "item": str(item),
                    "detail": item.detail,
                },
            )
        else:
            task_provide_pid_for_xml_uri.apply_async(
                kwargs={
                    "uri": uri,
                    "username": username,
                    "user_id": user_id,
                    "pid_v2": pid_v2,
                    "pid_v3": pid_v3,
                    "collection_acron": collection_acron,
                    "journal_acron": journal_acron,
                    "year": year,
                    "origin_date": origin_date,
                }
            )


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
