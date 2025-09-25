import logging
import sys

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from collection.models import Collection
from config import celery_app
from core.utils.jwt import issue_jwt_for_flask

from .api.v1.serializers import CollectionSerializer

User = get_user_model()
from tracker.models import UnexpectedEvent


@celery_app.task(bind=True)
def task_load_collections(self, user_id=None, username=None):
    if user_id:
        user = User.objects.get(pk=user_id)
    if username:
        user = User.objects.get(username=username)
    Collection.load(user)


def fetch_with_schema_guess(host_or_url, timeout=10):
    """
    Algumas coleções não possuem o schema no domínio, por isso é necessário
    tentar os schemas http e https para obter o resultado correto.
    """
    if "://" in host_or_url:
        return host_or_url
    
    for schema in ["http", "https"]:
        url = f"{schema}://{host_or_url}"
        try:
            resp = requests.post(url, timeout=timeout)
            resp.raise_for_status()
            return url
        except requests.exceptions.SSLError:
            continue
        except requests.exceptions.RequestException:
            continue


def _send_payload(url, headers, payload):
    url_with_schema = fetch_with_schema_guess(url)
    pattern_url = "http://172.23.0.1:8000" + settings.ENDPOINT_COLLECTION

    try:
        resp = requests.post(pattern_url, json=payload, headers=headers, timeout=5)
        if resp.status_code != 200:
            logging.error(f"Erro ao enviar dados de coleção para {url}. Status: {resp.status_code}. Body: {resp.text}")  
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "collection.tasks.build_collection_webhook",
                "url": url,
                "payload": payload,
                "headers": headers,
                "pattern_url": pattern_url,
            },
        )


@celery_app.task
def build_collection_webhook_for_all(event=False, headers=None):
    collections = Collection.objects.filter(domain__isnull=False, is_active=True)
    for collection in collections:
        build_collection_webhook.apply_async(
            kwargs=dict(
                event=event,
                collection_acron=collection.acron3,
                headers=headers,
            )
        )

@celery_app.task
def build_collection_webhook(event, collection_acron, headers=None):
    collection = Collection.objects.get(acron3=collection_acron)
    if not collection.domain:
        return None
    serializer = CollectionSerializer(collection)
    payload = {
        "event": event,
        "results": serializer.data,
    }
    token = issue_jwt_for_flask(
        sub="service:django",
        claims={"roles": ["m2m"], "scope": "ingest:write"}
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    _send_payload(url=collection.domain, headers=headers, payload=payload)


