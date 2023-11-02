import logging
import os
import sys
import traceback
from tempfile import TemporaryDirectory

import requests
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre
from requests.auth import HTTPBasicAuth

from pid_provider import exceptions
from pid_provider.models import PidProviderConfig, PidProviderXML, PidRequest

User = get_user_model()

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class PidProvider:
    """
    Recebe XML para validar ou atribuir o ID do tipo v3
    """

    def __init__(self):
        pass

    def provide_pid_for_xml_zip(
        self,
        zip_xml_file_path,
        user,
        filename=None,
        origin_date=None,
        force_update=None,
        is_published=None,
    ):
        """
        Fornece / Valida PID para o XML em um arquivo compactado

        Returns
        -------
            list of dict
        """
        try:
            for xml_with_pre in XMLWithPre.create(path=zip_xml_file_path):
                logging.info("provide_pid_for_xml_zip:")
                try:
                    registered = self.provide_pid_for_xml_with_pre(
                        xml_with_pre,
                        xml_with_pre.filename,
                        user,
                        origin_date=origin_date,
                        force_update=force_update,
                        is_published=is_published,
                    )
                    registered["filename"] = xml_with_pre.filename
                    logging.info(registered)
                    yield registered
                except Exception as e:
                    logging.exception(e)
                    yield {
                        "error_msg": f"Unable to provide pid for {zip_xml_file_path} {e}",
                        "error_type": str(type(e)),
                    }
        except Exception as e:
            logging.exception(e)
            yield {
                "error_msg": f"Unable to provide pid for {zip_xml_file_path} {e}",
                "error_type": str(type(e)),
            }

    def provide_pid_for_xml_uri(
        self,
        xml_uri,
        name,
        user,
        origin_date=None,
        force_update=None,
        is_published=None,
    ):
        """
        Fornece / Valida PID de um XML disponível por um URI

        Returns
        -------
            dict
        """
        try:
            xml_with_pre = list(XMLWithPre.create(uri=xml_uri))[0]
        except Exception as e:
            logging.exception(e)
            return {
                "error_msg": f"Unable to provide pid for {xml_uri} {e}",
                "error_type": str(type(e)),
            }
        else:
            return self.provide_pid_for_xml_with_pre(
                xml_with_pre,
                name,
                user,
                origin_date=origin_date,
                force_update=force_update,
                is_published=is_published,
            )

    def provide_pid_for_xml_with_pre(
        self,
        xml_with_pre,
        name,
        user,
        origin_date=None,
        force_update=None,
        is_published=None,
    ):
        """
        Fornece / Valida PID para o XML no formato de objeto de XMLWithPre
        """
        registered = PidProviderXML.register(
            xml_with_pre,
            name,
            user,
            origin_date=origin_date,
            force_update=force_update,
            is_published=is_published,
        )
        logging.info("")
        registered["xml_with_pre"] = xml_with_pre
        logging.info(f"provide_pid_for_xml_with_pre result: {registered}")
        return registered

    @classmethod
    def is_registered_xml_with_pre(cls, xml_with_pre):
        """
        Returns
        -------
            {"error_type": "", "error_message": ""}
            or
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_with_pre": self.xml_with_pre,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
            }
        """
        return PidProviderXML.get_registered(xml_with_pre)

    @classmethod
    def is_registered_xml_uri(cls, xml_uri):
        """
        Returns
        -------
            {"error_type": "", "error_message": ""}
            or
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_with_pre": self.xml_with_pre,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
            }
        """
        xml_with_pre = XMLWithPre.create(uri=xml_uri)
        return cls.is_registered_xml_with_pre(xml_with_pre)

    @classmethod
    def is_registered_xml_zip(cls, zip_xml_file_path):
        """
        Returns
        -------
            list of dict
                {"error_type": "", "error_message": ""}
                or
                {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_with_pre": self.xml_with_pre,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
                }
        """
        for xml_with_pre in XMLWithPre.create(path=zip_xml_file_path):
            registered = cls.is_registered_xml_with_pre(xml_with_pre)
            registered["filename"] = xml_with_pre.filename
            yield registered

    @classmethod
    def get_xml_uri(cls, v3):
        """
        Retorna XML URI ou None
        """
        return PidProviderXML.get_xml_uri(v3)


def provide_pid_for_xml_uri(
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
                "pid_provider.controller.provide_pid_for_xml_uri "
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
        for k, v in detail.items():
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
            datail=detail,
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

    return response
