from pid_provider.controller import PidProvider
from pid_provider.models import PidRequest, PidProviderXML


def request_pid_v3(user, uri, collection_acron, pid_v2):
    pp = PidProvider()

    try:
        year = pid_v2[10:14]
        pid_request = PidRequest.create_or_update(
            user=user,
            pid_v3=None,
            pid_v2=pid_v2,
            pkg_name=None,
            journal_acron=None,
            collection_acron=collection_acron,
            year=year,
            origin=uri,
            result_type=None,
            result_msg=None,
            xml_version=None,
        )
        response = pp.provide_pid_for_xml_uri(uri, pid_v2+".xml", user)
    except Exception as e:
        PidRequest.register_failure(
            e=e,
            user=user,
            collection_acron=collection_acron,
            pid_v2=pid_v2,
            origin=uri,
        )
    else:
        try:
            pid_v3 = response["v3"]
            xml_version = PidProviderXML.objects.get(v3=pid_v3).current_version
        except KeyError:
            pid_v3 = None

        pid_request = PidRequest.create_or_update(
            user=user,
            pid_v3=pid_v3,
            pid_v2=pid_v2,
            pkg_name=None,
            journal_acron=None,
            collection_acron=collection_acron,
            year=year,
            origin=uri,
            result_type=response.get("result_type") or "success",
            result_msg=response.get("result_msg") or response.get("result_message") or "ok",
            xml_version=xml_version,
        )
