import json
import logging
import os
from datetime import datetime, timedelta

import requests
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app
from core.utils.utils import fetch_data
from pid_provider.sources import am
from pid_provider.models import PidRequest
from pid_provider.controller import provide_pid_for_xml_uri

User = get_user_model()


# def fetch_data(uri, json=True, timeout=30, verify=True):
#     try:
#         data = core_fetch_data(uri, json=json, timeout=timeout, verify=verify)
#     except Exception as e:
#         return {}
#     else:
#         return data.json()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)

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


@celery_app.task(bind=True, name="provide_pid_for_opac_xml")
def provide_pid_for_opac_xml(self, username=None, user_id=None, collection_acron=None, documents=None, force_update=None):
    for pid_v3, article in documents.items():
        try:
            logging.info(article)
            acron = article["journal_acronym"]
            uri = f"https://www.scielo.br/j/{acron}/a/{pid_v3}/?format=xml"
            origin_date = datetime.strptime(
                article.get("update") or article.get("create"),
                "%a, %d %b %Y %H:%M:%S %Z",
            ).isoformat()[:10]

            task_provide_pid_for_xml_uri.apply_async(
                kwargs={
                    "uri": uri,
                    "username": username,
                    "user_id": user_id,
                    "pid_v2": None,
                    "pid_v3": pid_v3,
                    "collection_acron": collection_acron,
                    "journal_acron": acron,
                    "year": article["publication_date"][:4],
                    "origin_date": origin_date,
                    "force_update": force_update,
                }
            )
        except Exception as e:
            logging.exception(e)
            # kernel.register_failure(e, user=user, detail={"article": article})


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

    end_date = end_date or datetime.utcnow().isoformat()[:10]
    begin_date = begin_date or (datetime.utcnow() - timedelta(days=30)).isoformat()[:10]
    limit = limit or 100
    while True:
        try:
            uri = (
                f"https://www.scielo.br/api/v1/counter_dict?end_date={end_date}"
                f"&begin_date={begin_date}&limit={limit}&page={page}"
            )
            logging.info(uri)
            response = fetch_data(uri, json=True, timeout=30, verify=True)
            pages = pages or response["pages"]
            provide_pid_for_opac_xml.apply_async(
                kwargs={
                    "username": username,
                    "user_id": user_id,
                    "documents": response["documents"],
                    "force_update": force_update,
                }
            )
        except Exception as e:
            # por enquanto, o tratamento é para evitar interrupção do laço
            # TODO registrar o problema em um modelo de resultado de execução de tasks
            logging.exception("Error: processing {} {}".format(uri, e))

        finally:
            page += 1
            if page > pages:
                break


@celery_app.task(bind=True, name="provide_pid_for_am_xmls")
def provide_pid_for_am_xmls(
    self,
    username=None,
    user_id=None,
    items=None,
    force_update=None,
):
    if not items:
        raise ValueError("provide_pid_for_am_xmls requires pids")

    for item in items:
        try:
            uri = None
            collection_acron = item["collection_acron"]
            pid_v2 = item["pid_v2"]
            origin_date = item["processing_date"]
            uri = (
                f"https://articlemeta.scielo.org/api/v1/article/?"
                f"collection={collection_acron}&code={pid_v2}&format=xmlrsps"
            )
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
        except Exception as e:
            # por enquanto, o tratamento é para evitar interrupção do laço
            # TODO registrar o problema em um modelo de resultado de execução de tasks
            logging.exception("Error: processing {} {}".format(uri, e))


@celery_app.task(bind=True, name="harvest_pids")
def harvest_pids(
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

            provide_pid_for_am_xmls.apply_async(
                kwargs={
                    "username": username,
                    "user_id": user_id,
                    "items": items,
                    "force_update": force_update,
                }
            )

        except Exception as e:
            # por enquanto, o tratamento é para evitar interrupção do laço
            # TODO registrar o problema em um modelo de resultado de execução de tasks
            logging.exception("Error: processing {} {}".format(uri, e))


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
            logging.info(uri)
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
        except Exception as e:
            # TODO registrar o problema em um modelo de resultado de execução de tasks
            logging.exception(e)


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
    user = _get_user(self.request, username=username, user_id=user_id)
    provide_pid_for_xml_uri(
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
