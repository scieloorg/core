import os

from pid_provider.controller import PidProvider
from pid_provider.models import KernelXMLMigration, PidProviderXML


def load_xml(user, uri, name, acron, year):
    pp = PidProvider()

    try:
        pid_v3, ext = os.path.splitext(name)
        migration = KernelXMLMigration.create_or_update(
            user=user,
            pid_v3=pid_v3,
            acron=acron,
            year=year,
            error_type=None,
            error_msg=None,
            xml_version=None,
        )
        response = pp.provide_pid_for_xml_uri(uri, name, user)
        if response.get("error_type"):
            migration = KernelXMLMigration.create_or_update(
                user=user,
                pid_v3=pid_v3,
                acron=acron,
                year=year,
                error_type=response.get("error_type"),
                error_msg=response.get("error_msg") or response.get("error_message"),
            )
        else:
            migration = KernelXMLMigration.create_or_update(
                user=user,
                pid_v3=pid_v3,
                acron=acron,
                year=year,
                xml_version=PidProviderXML.objects.get(v3=pid_v3).current_version,
            )
            migration.error_msg = None
            migration.error_type = None
            migration.save()

    except Exception as e:
        migration = KernelXMLMigration.create_or_update(
            user=user,
            pid_v3=pid_v3,
            acron=acron,
            year=year,
            error_type=str(type(e)),
            error_msg=str(e),
        )
