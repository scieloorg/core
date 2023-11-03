import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from collection.models import Collection
from pid_provider.models import PidProviderXML, PidRequest, CollectionPidRequest

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

    if not force_update:
        # skip update
        try:
            if pid_v3:
                name = pid_v3 + ".xml"
                return PidProviderXML.objects.get(v3=pid_v3).data
            if pid_v2:
                name = pid_v2 + ".xml"
                return PidProviderXML.objects.get(v2=pid_v2).data
            return ValueError(
                "pid_provider.provide_pid_for_opac_and_am_xml "
                "requires pid_v2 or pid_v3"
            )
        except PidProviderXML.DoesNotExist:
            pass

    try:
        detail = {
            "pid_v2": pid_v2,
            "pid_v3": pid_v3,
            "collection_acron": collection_acron,
            "journal_acron": journal_acron,
            "year": year,
        }
        for k, v in list(detail.items()):
            if not v:
                detail.pop(k)

        logging.info(f"Request pid for {uri}")
        pp = PidProvider()
        response = pp.provide_pid_for_xml_uri(
            uri,
            name,
            user,
            origin_date=origin_date,
            force_update=force_update,
            is_published=True,
        )
    except Exception as e:
        return PidRequest.register_failure(
            e=e,
            user=user,
            origin=uri,
            origin_date=origin_date,
            detail=detail,
            v3=pid_v3,
        )

    try:
        pid_v3 = response["v3"]
    except KeyError:
        pid_v3 = None

    if not pid_v3:
        result_type = response.get("error_type") or response.get("result_type")
        result_msg = response.get("error_msg") or response.get("result_msg")

        # Guardar somente se houve problema
        pid_request = PidRequest.create_or_update(
            user=user,
            origin=uri,
            origin_date=origin_date,
            result_type=result_type,
            result_msg=result_msg,
            detail=detail,
        )
        return pid_request.data

    PidRequest.cancel_failure(
        user=user,
        origin=uri,
        origin_date=origin_date,
        v3=pid_v3,
        detail=detail,
    )
    try:
        CollectionPidRequest.create_or_update(
            user=user,
            collection=Collection.objects.get(acron3=collection_acron),
            end_date=origin_date,
        )
    except Exception as e:
        logging.exception(e)
    return response
