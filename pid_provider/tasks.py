import json
import os

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from pid_provider.sources import kernel

from config import celery_app


User = get_user_model()


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
def load_xmls(self, username=None, domain=None, article_list=None, jsonl_file_path=None):
    username = username or self.request.user.id
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
            args=(username, uri, pid_v3+".xml", acron, article["publication_year"]))


@celery_app.task(bind=True, name=_("load_xml_lists"))
def load_xml_lists(self, username=None, jsonl_files_path=None):
    username = username or self.request.user.id

    if not jsonl_files_path:
        raise ValueError("pid_provider.tasks.load_xml_lists requires jsonl_files_path")

    for filename in os.listdir(jsonl_files_path):
        load_xmls.apply_async(
            kwargs={
                "username": username,
                "jsonl_file_path": os.path.join(jsonl_files_path, filename),
            }
        )
