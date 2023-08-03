import json
import logging
import os
from datetime import datetime, timedelta

import requests
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from config import celery_app
from core.utils.utils import fetch_data
from pid_provider.sources import am, kernel

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


def _read_jsonl(jsonl_file_path):
    with open(jsonl_file_path, "r") as fp:
        for row in fp.readlines():
            yield json.loads(row.strip())


@celery_app.task(bind=True, name="load_xml")
def load_xml(
    self, username, uri, name, acron, year, origin_date=None, force_update=None
):
    user = _get_user(self.request, username=username)
    kernel.load_xml(user, uri, name, acron, year, origin_date, force_update)


@celery_app.task(bind=True, name="load_xmls")
def load_xmls(
    self,
    username=None,
    domain=None,
    article_list=None,
    jsonl_file_path=None,
    force_update=None,
):
    user = _get_user(self.request, username=username)

    domain = domain or "www.scielo.br"

    if jsonl_file_path:
        article_list = _read_jsonl(jsonl_file_path)

    if not article_list:
        raise ValueError("pid_provider.tasks.load_xmls requires article_list")

    for article in article_list:
        acron = article["acron"]
        pid_v3 = article["pid_v3"]
        origin_date = article.get("processing_date")
        uri = f"https://{domain}/j/{acron}/a/{pid_v3}/?format=xml"
        load_xml.apply_async(
            kwargs={
                "username": user.username,
                "uri": uri,
                "name": pid_v3 + ".xml",
                "acron": acron,
                "year": article["publication_year"],
                "origin_date": origin_date,
                "force_update": force_update,
            }
        )


@celery_app.task(bind=True, name="load_xml_lists")
def load_xml_lists(self, username=None, jsonl_files_path=None):
    if not jsonl_files_path:
        raise ValueError("pid_provider.tasks.load_xml_lists requires jsonl_files_path")

    for filename in os.listdir(jsonl_files_path):
        load_xmls.apply_async(
            kwargs={
                "username": username,
                "jsonl_file_path": os.path.join(jsonl_files_path, filename),
            }
        )


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
def provide_pid_for_opac_xml(self, username=None, documents=None, force_update=None):
    user = _get_user(self.request, username=username)
    for pid_v3, article in documents.items():
        try:
            logging.info(article)
            acron = article["journal_acronym"]
            xml_uri = f"https://www.scielo.br/j/{acron}/a/{pid_v3}/?format=xml"
            load_xml.apply_async(
                kwargs={
                    "username": user.username,
                    "uri": xml_uri,
                    "name": pid_v3 + ".xml",
                    "acron": acron,
                    "year": article["publication_date"][:4],
                    "origin_date": datetime.strptime(
                        article.get("update") or article.get("create"),
                        "%a, %d %b %Y %H:%M:%S %Z",
                    ).isoformat()[:10],
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
    begin_date=None,
    end_date=None,
    limit=None,
    pages=None,
    force_update=None,
):
    page = 1
    user = _get_user(self.request, username=username)
    logging.info(user)

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
                    "username": user.username,
                    "documents": response["documents"],
                    "force_update": force_update,
                }
            )
        except Exception as e:
            kernel.register_failure(e, user=user, detail={"uri": uri})
        finally:
            page += 1
            if page > pages:
                break


@celery_app.task(bind=True, name="provide_pid_for_am_xml")
def provide_pid_for_am_xml(
    self,
    username,
    collection_acron,
    pid_v2,
    processing_date=None,
    force_update=None,
):
    user = _get_user(self.request, username=username)
    uri = (
        f"https://articlemeta.scielo.org/api/v1/article/?"
        f"collection={collection_acron}&code={pid_v2}&format=xmlrsps"
    )
    am.request_pid_v3(
        user,
        uri,
        collection_acron,
        pid_v2,
        processing_date,
        force_update,
    )


@celery_app.task(bind=True, name="provide_pid_for_am_xmls")
def provide_pid_for_am_xmls(
    self,
    username=None,
    items=None,
    force_update=None,
):
    if not items:
        raise ValueError("provide_pid_for_am_xmls requires pids")

    for item in items:
        item.update({"username": username, "force_update": force_update})
        provide_pid_for_am_xml.apply_async(kwargs=item)


@celery_app.task(bind=True, name="harvest_pids")
def harvest_pids(
    self,
    username=None,
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
                    "items": items,
                    "force_update": force_update,
                }
            )

        except Exception as e:
            # por enquanto, o tratamento é para evitar interrupção do laço
            # TODO registrar o problema em um modelo de resultado de execução de tasks
            logging.exception("Error: processing {} {}".format(uri, e))
