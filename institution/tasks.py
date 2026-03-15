import logging
import sys

from django.db.models import Q

from config import celery_app
from tracker.models import UnexpectedEvent

logger = logging.getLogger(__name__)

RAW_ORG_FIELDS = [
    "raw_text",
    "raw_institution_name",
    "raw_country_name",
    "raw_country_code",
    "raw_state_name",
    "raw_state_acron",
    "raw_city_name",
]


def _has_raw_data_filter():
    """Build a Q filter matching instances where any RawOrganizationMixin field is filled."""
    q_filter = Q()
    for field in RAW_ORG_FIELDS:
        q_filter |= Q(**{f"{field}__isnull": False}) & ~Q(**{field: ""})
    return q_filter


@celery_app.task(bind=True, name="task_delete_unlinked_institutions_and_locations")
def task_delete_unlinked_institutions_and_locations(self):
    """
    Task to clean up unlinked Institution and Location objects.

    1. For all *History instances with RawOrganizationMixin data filled,
       set institution = None
    2. Delete Institution instances not linked to any *History
       (clear FK/M2M fields first)
    3. Delete all Location instances (clear FK/M2M fields first)
    """
    from institution.models import Institution
    from journal.models import (
        CopyrightHolderHistory,
        OwnerHistory,
        PublisherHistory,
        SponsorHistory,
    )
    from location.models import Location

    try:
        history_classes = [
            OwnerHistory,
            PublisherHistory,
            SponsorHistory,
            CopyrightHolderHistory,
        ]

        # Step 1: For *History instances with any RawOrganizationMixin field
        # filled, set institution = None
        raw_data_q = _has_raw_data_filter()
        for history_class in history_classes:
            updated = history_class.objects.filter(
                raw_data_q,
                institution__isnull=False,
            ).update(institution=None)
            logger.info(
                "Set institution=None for %d %s instances",
                updated,
                history_class.__name__,
            )

        # Step 2: Delete Institution instances not linked to any *History
        all_institution_ids = set(
            Institution.objects.values_list("id", flat=True)
        )
        linked_institution_ids = set()
        for history_class in history_classes:
            linked_institution_ids.update(
                history_class.objects.filter(
                    institution__institution__isnull=False,
                ).values_list("institution__institution_id", flat=True)
            )
        unlinked_ids = all_institution_ids - linked_institution_ids

        # Clear M2M fields for unlinked institutions
        for inst in Institution.objects.filter(id__in=unlinked_ids):
            inst.institution_type_scielo.clear()

        # Clear FK fields and delete
        Institution.objects.filter(id__in=unlinked_ids).update(
            institution_identification=None,
            location=None,
        )
        deleted_institutions = Institution.objects.filter(
            id__in=unlinked_ids
        ).count()
        Institution.objects.filter(id__in=unlinked_ids).delete()

        logger.info(
            "Deleted %d unlinked Institution instances", deleted_institutions
        )

        # Step 3: Delete all Location instances
        deleted_locations = Location.objects.count()
        Location.objects.update(city=None, state=None, country=None)
        Location.objects.all().delete()

        logger.info("Deleted %d Location instances", deleted_locations)

        return {
            "deleted_institutions": deleted_institutions,
            "deleted_locations": deleted_locations,
        }

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_delete_unlinked_institutions_and_locations",
            },
        )
        raise
