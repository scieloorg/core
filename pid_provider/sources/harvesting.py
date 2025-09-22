import logging
import sys
from datetime import datetime

from django.contrib.auth import get_user_model

# from django.utils.translation import gettext as _

from collection.models import Collection
from pid_provider.provider import PidProvider
from pid_provider.models import CollectionPidRequest, PidProviderXML
from tracker.models import UnexpectedEvent

User = get_user_model()

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def provide_pid_for_opac_and_am_xml(
    user,
    uri,
    pid_v2=None,
    pid_v3=None,
    collection_acron=None,
    journal_acron=None,
    year=None,
    origin_date=None,
    force_update=None,
):

    try:
        name = f"{pid_v3 or pid_v2 or datetime.now().isoformat().replace(':', '')}.xml"

        if not force_update:
            try:
                if pid_v3:
                    pid_xml = PidProviderXML.objects.get(v3=pid_v3)
                if pid_v2:
                    pid_xml = PidProviderXML.objects.get(v2=pid_v2)
                return pid_xml.data
            except PidProviderXML.DoesNotExist:
                pass

        detail = dict(
            pid_v2=pid_v2,
            pid_v3=pid_v3,
            collection_acron=collection_acron,
            journal_acron=journal_acron,
            year=year,
        )
        pp = PidProvider()
        response = pp.provide_pid_for_xml_uri(
            uri,
            name,
            user,
            origin_date=origin_date,
            force_update=force_update,
            is_published=True,
            detail=detail,
        )
        CollectionPidRequest.create_or_update(
            user=user,
            collection=Collection.objects.get(acron3=collection_acron),
            end_date=origin_date,
        )
        return response
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "provide_pid_for_opac_and_am_xml",
                "detail": dict(
                    pid_v2=pid_v2,
                    pid_v3=pid_v3,
                    collection_acron=collection_acron,
                    journal_acron=journal_acron,
                    year=year,
                    origin_date=origin_date,
                    force_update=force_update,
                ),
            },
        )
