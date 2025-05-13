import sys

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Q
from wagtail.images.models import Image

from collection.models import Collection
from config import celery_app
from core.utils.rename_dictionary_keys import rename_dictionary_keys
from core.utils.utils import fetch_data
from journal.models import (
    AMJournal,
    Journal,
    JournalLicense,
    JournalLogo,
    SciELOJournal,
)
from journal.sources import classic_website
from journal.sources.am_data_extraction import extract_value
from journal.sources.am_field_names import correspondencia_journal
from journal.sources.article_meta import (
    _register_journal_data,
    process_journal_article_meta,
)
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

        response = fetch_data(url_logo, json=False, timeout=1, verify=False)
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
def fetch_and_process_journal_logos_in_collection(self, collection_acron3=None, user_id=None,username=None):
    if collection_acron3:
        collection = Collection.objects.get(acron3=collection_acron3)
        journals = Journal.objects.filter(scielojournal__collection=collection)
    else:
        journals = Journal.objects.all()

    for journal in journals:
        fetch_and_process_journal_logo(
                journal_id=journal.id,
                user_id=user_id,
                username=username,
            )
        

@celery_app.task
def load_license_of_use_in_journal(issn_scielo=None, collection_acron3=None, user_id=None, username=None):
    params = {}
    if collection_acron3:
        collection = Collection.objects.get(acron3=collection_acron3)
        params["collection"] = collection
    if issn_scielo:
        params["scielo_issn"] = issn_scielo
    
    journals = AMJournal.objects.filter(**params)
    for journal in journals:
        if scielo_issn := journal.scielo_issn:
            if journal.data:
                license_data = extract_value(
                    rename_dictionary_keys(
                        journal.data, 
                        correspondencia_journal
                    ).get("license_of_use"))
                child_load_license_of_use_in_journal.apply_async(
                    kwargs=dict(
                        journal_issn=scielo_issn,
                        license_data=license_data,
                        username=username,
                        user_id=user_id,
                    )
                )

@celery_app.task
def child_load_license_of_use_in_journal(
    journal_issn, license_data, user_id=None, username=None
):
    user = _get_user(request=None, username=username, user_id=user_id)
    journal = Journal.objects.filter(
        scielojournal__issn_scielo=journal_issn, 
        scielojournal__collection__is_active=True
        ).prefetch_related(
            "scielojournal_set"
        ).distinct()
    if license_data:
        for item in journal:
            license_type = license_data.split("/")
            license = JournalLicense.create_or_update(license_type=license_type[0], user=user)
            item.journal_use_license = license
            item.save()
