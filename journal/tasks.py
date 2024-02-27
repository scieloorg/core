import sys

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from wagtail.images.models import Image

from core.utils.utils import fetch_data
from collection.models import Collection
from config import celery_app
from journal.models import SciELOJournal, JournalLogo, Journal
from journal.sources import classic_website
from journal.sources.article_meta import process_journal_article_meta, _register_journal_data
from tracker.models import UnexpectedEvent


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
                    load_data=load_data
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
    self, username=None, user_id=None, collection_acron=None, limit=None, load_data=None,
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
def load_journal_logo(self, user_id=None, username=None):
    for scielo_journal in SciELOJournal.objects.all():
        collection = scielo_journal.collection
        domain = collection.domain
        collection_acron3 = collection.acron3
        journal_acron = scielo_journal.journal_acron
        journal_id = scielo_journal.journal.id
        fetch_and_process_journal_logo.apply_async(kwargs=dict(collection_acron3=collection_acron3, domain=domain, journal_acron=journal_acron, journal_id=journal_id, username=username))

        
@celery_app.task(bind=True)
def fetch_and_process_journal_logo(self, collection_acron3, domain, journal_acron, journal_id, user_id=None, username=None):
    user = _get_user(self.request, username=username, user_id=user_id)
    if collection_acron3 == 'scl':
        url_logo = f"https://{domain}/media/images/{journal_acron}_glogo.gif"
    else:
        url_logo = f"http://{domain}/img/revistas/{journal_acron}/glogo.gif"
    
    try:
        response = fetch_data(url_logo, json=False, timeout=2, verify=True)
        logo_data = response
        img_wagtail = Image(title=journal_acron)
        img_wagtail.file.save(f"{journal_acron}_glogo.gif", ContentFile(logo_data))
        journal = Journal.objects.get(id=journal_id)
        JournalLogo.create_or_update(
            journal=journal,
            logo=img_wagtail,
            user=user
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "journal.tasks.fetch_and_process_logo_journal",
                "journal_id": journal_id,
                "domain": domain,
            },
        )


@celery_app.task(bind=True)
def assign_logo_to_all_journals(self, user_id=None, username=None):
    for journal in Journal.objects.all():
        update_journal_logo_if_exists.apply_async(kwargs=dict(
            journal_id=journal.id,
        ))

@celery_app.task(bind=True)
def update_journal_logo_if_exists(self, journal_id, user_i=None, username=None):
    journal = Journal.objects.get(id=journal_id)
    if journal_logo := JournalLogo.objects.filter(journal=journal).first():
        journal.logo = journal_logo.logo
        journal.save()
        