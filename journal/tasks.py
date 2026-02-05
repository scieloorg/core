import logging
import sys

from celery import group
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Prefetch
from wagtail.images.models import Image

from collection.models import Collection
from config import celery_app
from core.utils.rename_dictionary_keys import rename_dictionary_keys
from core.utils.utils import _get_user, fetch_data
from journal import controller
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

logger = logging.getLogger(__name__)


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


from urllib.parse import urlparse


def _normalize_collection_domain(url, strip_www=False):
    parsed = urlparse(url if "://" in url else "http://" + url)
    host = parsed.netloc or parsed.path

    if strip_www and host.startswith("www."):
        host = host[4:]
    return host


def _build_logo_url(collection, journal_acron):
    """Build logo URL based on collection type."""
    try:
        domain = _normalize_collection_domain(collection.domain)
    except Exception as e:
        logging.error(f"Error normalizing collection domain: {e}")
        return None

    collection_acron3 = collection.acron3

    if collection_acron3 == "scl":
        return f"https://{domain}/media/images/{journal_acron}_glogo.gif"
    else:
        return f"http://{domain}/img/revistas/{journal_acron}/glogo.gif"


@celery_app.task(bind=True)
def fetch_and_process_journal_logo(
    self,
    journal_id,
    user_id=None,
    username=None,
):
    try:
        journal = Journal.objects.prefetch_related(
            Prefetch(
                "scielojournal_set",
                queryset=SciELOJournal.objects.select_related("collection").filter(
                    collection__is_active=True
                ),
                to_attr="active_collections",
            )
        ).get(id=journal_id)
        scielo_journal = journal.scielojournal_set.first()
        collection = scielo_journal.collection
        journal_acron = scielo_journal.journal_acron

        user = _get_user(self.request, username=username, user_id=user_id)
        url_logo = _build_logo_url(collection, journal_acron)
        if not url_logo:
            return None

        response = fetch_data(url_logo, json=False, timeout=30, verify=True)
        img_wagtail, created = Image.objects.get_or_create(
            title=journal_acron,
            defaults={
                "file": ContentFile(response, name=f"{journal_acron}_glogo.gif"),
            },
        )
        journal_logo = JournalLogo.create_or_update(
            journal=journal, logo=img_wagtail, user=user
        )
        if not journal.logo and journal.logo != img_wagtail:
            journal.logo = journal_logo.logo
        journal.save()
        logger.info(f"Successfully processed logo for journal {journal_id}")
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="journal.tasks.fetch_and_process_journal_logo",
            detail={
                "function": "journal.tasks.fetch_and_process_journal_logo",
                "journal_title": journal.title,
                "url_logo": url_logo,
                "domain": collection.domain,
            },
        )


@celery_app.task(bind=True)
def fetch_and_process_journal_logos_in_collection(
    self, collection_acron3=None, user_id=None, username=None
):
    try:
        if collection_acron3:
            if not Collection.objects.filter(acron3=collection_acron3).exists():
                raise ValueError(
                    f"Collection with acron3 '{collection_acron3}' does not exist"
                )
            journals = Journal.objects.filter(
                scielojournal__collection__acron3=collection_acron3
            ).values_list("id", flat=True)
        else:
            journals = Journal.objects.values_list("id", flat=True)

        journal_ids = list(journals)
        total_journals = len(journal_ids)

        if total_journals == 0:
            logger.warning(f"No journals found for collection {collection_acron3}")
            return None

        tasks = []
        for journal_id in journal_ids:
            task = celery_app.signature(
                "journal.tasks.fetch_and_process_journal_logo",
                kwargs={
                    "journal_id": journal_id,
                    "user_id": user_id,
                    "username": username,
                },
            )
            tasks.append(task)
        # Executa melhor tasks sem
        job = group(tasks)
        result = job()
        logger.info(
            f"Started processing {total_journals} journal logos "
            f"for collection {collection_acron3 or 'all'}"
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="journal.tasks.fetch_and_process_journal_logos_in_collection",
            detail={
                "task": "journal.tasks.fetch_and_process_journal_logos_in_collection",
                "collection_acron3": collection_acron3,
                "error_type": exc_type.__name__ if exc_type else "Unknown",
            },
        )


@celery_app.task
def load_license_of_use_in_journal(
    issn_scielo=None, collection_acron3=None, user_id=None, username=None
):
    params = {}
    if collection_acron3:
        collection = Collection.objects.get(acron3=collection_acron3)
        params["collection"] = collection
    if issn_scielo:
        params["pid"] = issn_scielo

    journals = AMJournal.objects.filter(**params)
    for journal in journals:
        if scielo_issn := journal.scielo_issn:
            if journal.data:
                license_data = extract_value(
                    rename_dictionary_keys(journal.data, correspondencia_journal).get(
                        "license_of_use"
                    )
                )
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
    journal = (
        Journal.objects.filter(
            scielojournal__issn_scielo=journal_issn,
            scielojournal__collection__is_active=True,
        )
        .prefetch_related("scielojournal_set")
        .distinct()
    )
    if license_data:
        for item in journal:
            license_type = license_data.split("/")
            license = JournalLicense.create_or_update(
                license_type=license_type[0], user=user
            )
            item.journal_use_license = license
            item.save()


@celery_app.task(bind=True, name="task_export_journals_to_articlemeta")
def task_export_journals_to_articlemeta(
    self,
    collection_acron_list=None,
    journal_acron_list=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=None,
    user_id=None,
    username=None,
):
    """
    Export journals to ArticleMeta Database with flexible filtering.
    
    Args:
        collection_acron_list: Filter by collections acronyms (e.g., ['scl', 'mex'])
        journal_acron_list: Filter by journal acronyms
        from_date: Start date for filtering
        until_date: End date for filtering
        days_to_go_back: Number of days to go back from current date
        force_update: Force update existing records
        user_id: User ID for authentication
        username: Username for authentication
    
    Returns:
        dict: Result of bulk export operation
    
    Raises:
        Exception: Any unexpected error during export
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        
        result = controller.bulk_export_journals_to_articlemeta(
            user=user,
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_date=from_date,
            until_date=until_date,
            days_to_go_back=days_to_go_back,
            force_update=force_update,
        )
        
        return result
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_export_journals_to_articlemeta",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "from_date": from_date,
                "until_date": until_date,
                "days_to_go_back": days_to_go_back,
                "force_update": force_update,
                "user_id": user_id,
                "username": username,
                "task_id": self.request.id if hasattr(self.request, 'id') else None,
            },
        )
        
        # Re-raise para que o Celery possa tratar a exceção adequadamente
        raise


@celery_app.task(bind=True, name="task_replace_institution_by_raw_institution")
def task_replace_institution_by_raw_institution(
    self,
    username=None,
    user_id=None,
    collection_acron_list=None,
    journal_issns=None,
):
    """
    Task to populate RawOrganizationMixin fields from AMJournal records.
    
    This task extracts institution data from journal.models.AMJournal records and
    populates the raw organization fields in PublisherHistory, OwnerHistory,
    CopyrightHolderHistory, and SponsorHistory.
    
    Args:
        username: User name for authentication
        user_id: User ID for authentication
        collection_acron_list: List of collection acronyms to filter journals
        journal_issns: List of journal ISSNs to filter journals
    
    Returns:
        Dict with processing statistics
    """
    from journal.sources.am_data_extraction import extract_value
    
    user = _get_user(self.request, username=username, user_id=user_id)
    
    try:
        params = {}
        # Filter by collection if provided
        if collection_acron_list:
            from collection.models import Collection
            collections = Collection.objects.filter(acron3__in=collection_acron_list)
            params["collection__in"] = collections
        
        # Filter by journal ISSN if provided
        if journal_issns:
            params["pid__in"] = journal_issns
        
        processed_count = 0
        error_count = 0
        
        for am_journal in AMJournal.objects.filter(**params).iterator():
            try:
                # Extract data from AMJournal
                data = am_journal.data

                # Skip if no data
                if not data:
                    continue
                
                # Get the corresponding journal
                try:
                    scielo_journal = SciELOJournal.objects.get(
                        issn_scielo=am_journal.pid,
                        collection=am_journal.collection
                    )
                    journal = scielo_journal.journal
                except SciELOJournal.DoesNotExist:
                    logger.warning(
                        f"SciELOJournal not found for pid={am_journal.pid}, "
                        f"collection={am_journal.collection}"
                    )
                    continue
                
                # Extract publisher/owner data
                publisher = extract_value(data.get("publisher_name"))
                publisher_country = extract_value(data.get("publisher_country"))
                publisher_state = extract_value(data.get("publisher_state"))
                publisher_city = extract_value(data.get("publisher_city"))
                
                # Extract sponsor data
                sponsor = extract_value(data.get("sponsors"))
                
                # Extract copyright holder data
                copyright_holder = extract_value(data.get("copyrighter"))
                
                # Update PublisherHistory and OwnerHistory records
                if publisher:
                    if isinstance(publisher, str):
                        publisher = [publisher]
                    
                    # Filter non-empty publisher names
                    for _publisher in publisher:
                        if not _publisher:
                            continue
                        journal.add_publisher(
                            user=user,
                            original_data=_publisher,
                            location=None,
                            raw_institution_name=_publisher,
                            raw_country_name=publisher_country,
                            raw_state_name=publisher_state,
                            raw_city_name=publisher_city,
                        )
                        journal.add_owner(
                            user=user,
                            original_data=_publisher,
                            location=None,
                            raw_institution_name=_publisher,
                            raw_country_name=publisher_country,
                            raw_state_name=publisher_state,
                            raw_city_name=publisher_city,
                        )
                
                # Update SponsorHistory records
                if sponsor:
                    if isinstance(sponsor, str):
                        sponsor = [sponsor]
                    
                    for _sponsor in sponsor:
                        if not _sponsor:
                            continue
                        journal.add_sponsor(
                            user=user,
                            original_data=_sponsor,
                            location=None,
                            raw_institution_name=_sponsor,
                        )
                
                # Update CopyrightHolderHistory records
                if copyright_holder:
                    if isinstance(copyright_holder, str):
                        copyright_holder = [copyright_holder]
                    
                    for _copyright_holder in copyright_holder:
                        if not _copyright_holder:
                            continue
                        journal.add_copyright_holder(
                            user=user,
                            original_data=_copyright_holder,
                            location=None,
                            raw_institution_name=_copyright_holder,
                        )

                processed_count += 1
                
            except Exception as e:
                error_count += 1
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "task": "task_replace_institution_by_raw_institution",
                        "am_journal_id": am_journal.id,
                        "pid": am_journal.pid,
                        "collection": str(am_journal.collection) if am_journal.collection else None,
                    },
                )
                logger.error(
                    f"Error processing AMJournal {am_journal.id}: {e}"
                )
        
        result = {
            "processed_count": processed_count,
            "error_count": error_count,
        }
        
        logger.info(
            f"task_replace_institution_by_raw_institution completed: {result}"
        )
        
        return result
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_replace_institution_by_raw_institution",
                "collection_acron_list": collection_acron_list,
                "journal_issns": journal_issns,
                "user_id": user_id,
                "username": username,
            },
        )
        raise


@celery_app.task(bind=True, name="task_export_journal_to_articlemeta")
def task_export_journal_to_articlemeta(
    self,
    journal_acron,
    collection_acron,
    force_update=True,
    user_id=None,
    username=None,
):
    """
    Export a single journal to ArticleMeta Database.
    
    Args:
        journal_acron: Journal acronym to export
        collection_acron: Collection acronym
        force_update: Force update existing records (default: True)
        user_id: User ID for authentication
        username: Username for authentication
    
    Returns:
        dict: Result of bulk export operation
    
    Raises:
        Exception: Any unexpected error during export
    """
    try:
        # Validações básicas
        if not journal_acron:
            raise ValueError("journal_acron is required")
        if not collection_acron:
            raise ValueError("collection_acron is required")
        
        user = _get_user(self.request, username=username, user_id=user_id)
        
        result = controller.bulk_export_journals_to_articlemeta(
            user=user,
            collection_acron_list=[collection_acron],
            journal_acron_list=[journal_acron],
            force_update=force_update,
        )
        
        return result
        
    except ValueError as e:
        # Para erros de validação, registra mas não re-raise
        # pois são erros esperados de uso incorreto
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_export_journal_to_articlemeta",
                "journal_acron": journal_acron,
                "collection_acron": collection_acron,
                "force_update": force_update,
                "user_id": user_id,
                "username": username,
                "task_id": self.request.id if hasattr(self.request, 'id') else None,
                "error_type": "validation_error",
            },
        )
        
        # Re-raise ValueError para que o Celery marque a task como falha
        raise
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_export_journal_to_articlemeta",
                "journal_acron": journal_acron,
                "collection_acron": collection_acron,
                "force_update": force_update,
                "user_id": user_id,
                "username": username,
                "task_id": self.request.id if hasattr(self.request, 'id') else None,
                "error_type": "unexpected_error",
            },
        )
        
        # Re-raise para que o Celery possa tratar a exceção adequadamente
        raise


@celery_app.task(bind=True, name="migrate_institution_data_to_raw_institution")
def migrate_institution_data_to_raw_institution(
    self,
    username=None,
    user_id=None,
):
    """
    Task to migrate data from institution field to RawOrganizationMixin fields
    in History models (PublisherHistory, OwnerHistory, SponsorHistory, CopyrightHolderHistory).
    
    This task:
    1. Iterates through all History records that have an institution field populated
    2. Copies data from institution to the corresponding raw_* fields
    3. Sets institution = None after migration
    
    Args:
        username: User name for authentication
        user_id: User ID for authentication
    
    Returns:
        Dict with migration statistics
    """
    from journal.models import (
        PublisherHistory,
        OwnerHistory,
        SponsorHistory,
        CopyrightHolderHistory,
    )
    
    user = _get_user(self.request, username=username, user_id=user_id)
    
    try:
        stats = {
            "PublisherHistory": {"migrated": 0, "errors": 0},
            "OwnerHistory": {"migrated": 0, "errors": 0},
            "SponsorHistory": {"migrated": 0, "errors": 0},
            "CopyrightHolderHistory": {"migrated": 0, "errors": 0},
        }
        
        # Define the history classes to process
        history_classes = [
            PublisherHistory,
            OwnerHistory,
            SponsorHistory,
            CopyrightHolderHistory,
        ]
        
        for history_class in history_classes:
            class_name = history_class.__name__
            logger.info(f"Processing {class_name}...")
            
            # Get all records that have institution populated
            records = history_class.objects.filter(institution__isnull=False)
            
            for record in records:
                try:
                    institution = record.institution.institution
                    
                    # Skip if institution is None
                    if not institution:
                        continue
                    
                    # Extract data from institution
                    institution_identification = institution.institution_identification
                    
                    # Populate raw_* fields
                    if institution_identification:
                        # Set raw_institution_name from name or acronym
                        if institution_identification.name:
                            record.raw_institution_name = institution_identification.name
                        elif institution_identification.acronym:
                            record.raw_institution_name = institution_identification.acronym
                    
                    # Set location-related fields
                    if institution.location:
                        location = institution.location
                        
                        if location.city:
                            record.raw_city_name = location.city.name
                        
                        if location.state:
                            record.raw_state_name = location.state.name
                            record.raw_state_acron = location.state.acronym
                        
                        if location.country:
                            record.raw_country_name = location.country.name
                            record.raw_country_code = location.country.acron3
                    
                    # Build raw_text with all available information
                    text_parts = []
                    if institution_identification:
                        if institution_identification.name:
                            text_parts.append(institution_identification.name)
                        if institution_identification.acronym:
                            text_parts.append(f"({institution_identification.acronym})")
                    
                    if institution.level_1:
                        text_parts.append(institution.level_1)
                    if institution.level_2:
                        text_parts.append(institution.level_2)
                    if institution.level_3:
                        text_parts.append(institution.level_3)
                    
                    if text_parts:
                        record.raw_text = " | ".join(text_parts)
                    
                    # Set institution to None
                    record.institution = None
                    
                    # Save the record
                    record.save()
                    
                    stats[class_name]["migrated"] += 1
                    
                except Exception as e:
                    stats[class_name]["errors"] += 1
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "task": "migrate_institution_data_to_raw_institution",
                            "model": class_name,
                            "record_id": record.id,
                        },
                    )
                    logger.error(
                        f"Error migrating {class_name} record {record.id}: {e}"
                    )
        
        logger.info(
            f"Migration completed: {stats}"
        )
        
        return stats
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "migrate_institution_data_to_raw_institution",
                "user_id": user_id,
                "username": username,
            },
        )
        raise
