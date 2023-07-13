import logging
import os
import sys
import traceback
from tempfile import TemporaryDirectory

import requests
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from requests.auth import HTTPBasicAuth

from pid_provider import exceptions
from pid_provider.models import PidProviderConfig, PidProviderXML
from xmlsps.xml_sps_lib import XMLWithPre

User = get_user_model()

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class PidProvider:
    """
    Recebe XML para validar ou atribuir o ID do tipo v3
    """

    def __init__(self):
        pass

    def provide_pid_for_xml_zip(self, zip_xml_file_path, user):
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

    def provide_pid_for_xml_uri(self, xml_uri, name, user):
        """
        Fornece / Valida PID de um XML disponível por um URI

        Returns
        -------
            dict
        """
        try:
            xml_with_pre = XMLWithPre.create(uri=xml_uri)
        except Exception as e:
            logging.exception(e)
            return {
                "error_msg": f"Unable to provide pid for {xml_uri} {e}",
                "error_type": str(type(e)),
            }
        else:
            return self.provide_pid_for_xml_with_pre(xml_with_pre, name, user)

    def provide_pid_for_xml_with_pre(self, xml_with_pre, name, user):
        """
        Fornece / Valida PID para o XML no formato de objeto de XMLWithPre
        """
        registered = PidProviderXML.register(
            xml_with_pre,
            name,
            user,
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
