import os

from pid_provider.controller import PidProvider
from pid_provider.models import PidRequest


def load_xml(user, uri, name, acron, year):

    pp = PidProvider()

    try:
        pid_v3, ext = os.path.splitext(name)
        response = pp.provide_pid_for_xml_uri(uri, name, user)
    except Exception as e:
        return PidRequest.register_failure(
            e=e,
            user=user,
            origin=uri,
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
            result_type=result_type,
            result_msg=result_msg,
        )
