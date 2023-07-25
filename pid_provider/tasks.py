import json
import os
import logging
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
import requests

from pid_provider.sources import kernel, am

# from core.utils.utils import fetch_data
from config import celery_app

User = get_user_model()


def fetch_data(uri, json=True, timeout=30, verify=True):
    try:
        data = requests.get(uri, timeout=timeout)
    except Exception as e:
        return {}
    else:
        return data.json()


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


@celery_app.task(bind=True, name=_("load_xml"))
def load_xml(self, username, uri, name, acron, year):
    user = _get_user(self.request, username=username)
    kernel.load_xml(user, uri, name, acron, year)


@celery_app.task(bind=True, name=_("load_xmls"))
def load_xmls(
    self, username=None, domain=None, article_list=None, jsonl_file_path=None
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
        uri = f"https://{domain}/j/{acron}/a/{pid_v3}/?format=xml"
        load_xml.apply_async(
            args=(
                user.username,
                uri,
                pid_v3 + ".xml",
                acron,
                article["publication_year"],
            )
        )


@celery_app.task(bind=True, name=_("load_xml_lists"))
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
{"begin_date":"2023-06-01 00-00-00","collection":"scl","dictionary_date":"Sat, 01 Jul 2023 00:00:00 GMT","documents":{"JFhVphtq6czR6PHMvC4w38N":{"aop_pid":"","create":"Sat, 28 Nov 2020 23:42:43 GMT","default_language":"en","journal_acronym":"aabc","pid":"S0001-37652012000100017","pid_v1":"S0001-3765(12)08400117","pid_v2":"S0001-37652012000100017","pid_v3":"JFhVphtq6czR6PHMvC4w38N","publication_date":"2012-05-22","update":"Fri, 30 Jun 2023 20:57:30 GMT"},"ZZYxjr9xbVHWmckYgDwBfTc":{"aop_pid":"","create":"Sat, 28 Nov 2020 23:42:37 GMT","default_language":"en","journal_acronym":"aabc","pid":"S0001-37652012000100014","pid_v1":"S0001-3765(12)08400114","pid_v2":"S0001-37652012000100014","pid_v3":"ZZYxjr9xbVHWmckYgDwBfTc","publication_date":"2012-02-24","update":"Fri, 30 Jun 2023 20:56:59 GMT"},"pxXcvQXT8jQc8mzWz8JKTcq":{"aop_pid":"","create":"Sat, 28 Nov 2020 23:42:35 GMT","default_language":"en","journal_acronym":"aabc","pid":"S0001-37652012000100006","pid_v1":"S0001-3765(12)08400106","pid_v2":"S0001-37652012000100006","pid_v3":"pxXcvQXT8jQc8mzWz8JKTcq","publication_date":"2012-05-22","update":"Fri, 30 Jun 2023 20:56:50 GMT"},"ttD5sS3n4YcP8LVN7w6nJ4z":{"aop_pid":"","create":"Sat, 28 Nov 2020 23:42:33 GMT","default_language":"en","journal_acronym":"aabc","pid":"S0001-37652012000100008","pid_v1":"S0001-3765(12)08400108","pid_v2":"S0001-37652012000100008","pid_v3":"ttD5sS3n4YcP8LVN7w6nJ4z","publication_date":"2012-02-02","update":"Fri, 30 Jun 2023 20:56:37 GMT"},"wxcRCTCY3VnM4H8WSGF7TyK":{"aop_pid":"","create":"Sun, 29 Nov 2020 08:38:58 GMT","default_language":"en","journal_acronym":"aabc","pid":"S0001-37652012000200001","pid_v1":"S0001-3765(12)08400201","pid_v2":"S0001-37652012000200001","pid_v3":"wxcRCTCY3VnM4H8WSGF7TyK","publication_date":"2012-05-25","update":"Fri, 30 Jun 2023 20:56:41 GMT"}},"end_date":"2023-07-01 00-00-00","limit":5,"page":1,"pages":410,"total":2050}
"""
@celery_app.task(bind=True, name=_("load_xmls_from_opac"))
def load_xmls_from_opac(self, username=None, documents=None):
    user = _get_user(self.request, username=username)
    for pid_v3, article in documents.items():
        try:
            logging.info(article)
            acron = article["journal_acronym"]
            xml_uri = f"https://www.scielo.br/j/{acron}/a/{pid_v3}/?format=xml"
            load_xml.apply_async(
                args=(
                    user.username,
                    xml_uri,
                    pid_v3 + ".xml",
                    acron,
                    article["publication_date"][:4],
                )
            )
        except Exception as e:
            kernel.register_failure(e, user=user, detail={"article": article})


@celery_app.task(bind=True, name=_("load_xml_lists_from_opac"))
def load_xml_lists_from_opac(
    self, username=None, begin_date=None, end_date=None, limit=None, pages=None
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
            load_xmls_from_opac.apply_async(args=(user.username, response["documents"]))
        except Exception as e:
            kernel.register_failure(e, user=user, detail={"uri": uri})
        finally:
            page += 1
            if page > pages:
                break


@celery_app.task(bind=True, name=_("provide_pid_for_am_xml"))
def provide_pid_for_am_xml(
    self, username=None, collection_acron=None, pid_v2=None,
):
    user = _get_user(self.request, username=username)
    uri = (
        f"https://articlemeta.scielo.org/api/v1/article/?"
        f"collection={collection_acron}&code={pid_v2}&format=xmlrsps"
    )
    am.request_pid_v3(user, uri, collection_acron, pid_v2)
