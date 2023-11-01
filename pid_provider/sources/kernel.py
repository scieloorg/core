import logging
import os

from pid_provider.controller import PidProvider
from pid_provider.models import PidRequest, PidProviderXML


def load_xml(user, uri, name, acron, year, origin_date=None, force_update=None):
    pid_v3, ext = os.path.splitext(name)

    if not force_update:
        # skip update
        try:
            return PidProviderXML.objects.get(v3=pid_v3).data
        except PidProviderXML.DoesNotExist:
            pass

    try:
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
        )
        return pid_request.data
    return response
