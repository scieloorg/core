import logging
import sys

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from wagtail.images.models import Image

from core.utils.utils import fetch_data
from collection.models import Collection
from config import celery_app
from journal.models import Journal, JournalLogo
from journal.sources import classic_website
from journal.sources.article_meta import (
    process_journal_article_meta,
    _register_journal_data,
)
from tracker.models import UnexpectedEvent


User = get_user_model()

logger = logging.getLogger(__name__)

def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


@celery_app.task(bind=True)
def load_journal_from_classic_website(self, username=None, user_id=None):
    user = _get_user(self.request, username=username, user_id=user_id)
    classic_website.load(user)


@celery_app.task(bind=True)
def load_journal_from_article_meta(
    self, username=None, user_id=None, limit=None, collection_acron=None, load_data=None
):
    try:
        if collection_acron:
            items = Collection.objects.filter(
                collection_type="journals", acron3=collection_acron
            ).iterator()
        else:
            items = Collection.objects.filter(collection_type="journals").iterator()

        for item in items:
            load_journal_from_article_meta_for_one_collection.apply_async(
                kwargs=dict(
                    user_id=user_id,
                    username=username,
                    collection_acron=item.acron3,
                    limit=limit,
                    load_data=load_data,
                )
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "journal.tasks.load_journal_from_article_meta",
            },
        )


@celery_app.task(bind=True)
def load_journal_from_article_meta_for_one_collection(
    self,
    username=None,
    user_id=None,
    collection_acron=None,
    limit=None,
    load_data=None,
):
    user = _get_user(self.request, username=username, user_id=user_id)
    try:
        # Se load_data igual a True
        # Carrega os dados obtidos de article meta em AMJournal
        # Se load_data igual a Fase
        # Carrega os dados em Journal a partir de AMJournal.
        if load_data:
            process_journal_article_meta(
                collection=collection_acron, limit=limit, user=user
            )
        else:
            _register_journal_data(user=user, collection_acron3=collection_acron)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "journal.tasks.load_journal_from_article_meta_for_one_collection",
                "collection_acron": collection_acron,
            },
        )


@celery_app.task(bind=True)
def fetch_and_process_journal_logo(
    self,
    journal_id,
    user_id=None,
    username=None,
):
    try:
        journal = Journal.objects.get(id=journal_id)
        scielo_journal = journal.scielojournal_set.first()
        collection = scielo_journal.collection
        domain = collection.domain
        collection_acron3 = collection.acron3
        journal_acron = scielo_journal.journal_acron

        user = _get_user(self.request, username=username, user_id=user_id)
        if collection_acron3 == "scl":
            url_logo = f"https://{domain}/media/images/{journal_acron}_glogo.gif"
        else:
            url_logo = f"http://{domain}/img/revistas/{journal_acron}/glogo.gif"

        response = fetch_data(url_logo, json=False, timeout=1, verify=True)
        logo_data = response
        img_wagtail = Image(title=journal_acron)
        img_wagtail.file.save(f"{journal_acron}_glogo.gif", ContentFile(logo_data))
        
        journal_logo = JournalLogo.create_or_update(journal=journal, logo=img_wagtail, user=user)
        journal.logo = journal_logo.logo
        journal.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "journal.tasks.fetch_and_process_journal_logo",
                "journal_title": journal.title,
                "url_logo": url_logo,
                "domain": domain,
            },
        )


@celery_app.task(bind=True)
def update_journal_valid_field(self, journal_acron=None, acron_collection=None):
    """
    Atualiza o campo 'valid' para False nos objetos Journal.
    """
    if journal_acron and acron_collection:
        num_updated = Journal.objects.filter(scielojournal__journal_acron=journal_acron,
        scielojournal__collection__acron3=acron_collection).update(valid=False)
    else:
        num_updated = Journal.objects.all().update(valid=False)
    logging.info(f"Updated {num_updated} journals to valid=False.")
    

