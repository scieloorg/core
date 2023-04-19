import logging

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from files_storage.controller import FilesStorageManager
from pid_provider.models import PidProviderXML
from xmlsps import xml_sps_lib

User = get_user_model()

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class PidProvider:
    """
    Recebe XML para validar ou atribuir o ID do tipo v3
    """

    def __init__(self, files_storage_name):
        self.files_storage_manager = FilesStorageManager(files_storage_name)

    @property
    def push_xml_content(self):
        return self.files_storage_manager.push_xml_content

    def provide_pid_for_xml_zip(self, zip_xml_file_path, user, synchronized=None):
        """
        Fornece / Valida PID para o XML em um arquivo compactado

        Returns
        -------
            list of dict
                {
                    "v3": self.v3,
                    "v2": self.v2,
                    "aop_pid": self.aop_pid,
                    "xml_uri": self.xml_uri,
                    "article": self.article,
                    "created": self.created.isoformat(),
                    "updated": self.updated.isoformat(),
                    "xml_changed": boolean,
                    "record_status": created | updated | retrieved
                }
                or
                {
                    "error_type": self.error_type,
                    "error_message": self.error_message,
                    "id": self.finger_print,
                    "basename": self.basename,
                }
        """
        for item in xml_sps_lib.get_xml_items(zip_xml_file_path):
            xml_with_pre = item.pop("xml_with_pre")
            # {"filename": item: "xml": xml}
            registered = self.provide_pid_for_xml_with_pre(
                xml_with_pre,
                item["filename"],
                user,
                synchronized,
            )
            registered.update(item)
            yield registered

    def provide_pid_for_xml_uri(self, xml_uri, filename, user, synchronized=None):
        """
        Fornece / Valida PID de um XML disponível por um URI

        Returns
        -------
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_uri": self.xml_uri,
                "article": self.article,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
                "xml_changed": boolean,
                "record_status": created | updated | retrieved
            }
            or
            {
                "error_type": self.error_type,
                "error_message": self.error_message,
                "id": self.finger_print,
                "basename": self.basename,
            }"""
        xml_with_pre = xml_sps_lib.get_xml_with_pre_from_uri(xml_uri)
        return self.provide_pid_for_xml_with_pre(
            xml_with_pre, filename, user, synchronized
        )

    def provide_pid_for_xml_with_pre(
        self, xml_with_pre, filename, user, synchronized=None
    ):
        """
        Fornece / Valida PID para o XML no formato de objeto de XMLWithPre

        Returns
        -------
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_uri": self.xml_uri,
                "article": self.article,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
                "xml_changed": boolean,
                "record_status": created | updated | retrieved
            }
            or
            {
                "error_type": self.error_type,
                "error_message": self.error_message,
                "id": self.finger_print,
                "basename": self.basename,
            }
        """
        return PidProviderXML.register(
            xml_with_pre,
            filename,
            user,
            self.push_xml_content,
            synchronized,
        )

    @classmethod
    def is_registered_xml_with_pre(cls, xml_with_pre):
        """
        Returns
        -------
            {"error": ""}
            or
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_uri": self.xml_uri,
                "article": self.article,
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
            {"error": ""}
            or
            {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_uri": self.xml_uri,
                "article": self.article,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
            }
        """
        xml_with_pre = xml_sps_lib.get_xml_with_pre_from_uri(xml_uri)
        return cls.is_registered_xml_with_pre(xml_with_pre)

    @classmethod
    def is_registered_xml_zip(cls, zip_xml_file_path):
        """
        Returns
        -------
            list of dict
                {"error": ""}
                or
                {
                "v3": self.v3,
                "v2": self.v2,
                "aop_pid": self.aop_pid,
                "xml_uri": self.xml_uri,
                "article": self.article,
                "created": self.created.isoformat(),
                "updated": self.updated.isoformat(),
                }
        """
        for item in xml_sps_lib.get_xml_items(zip_xml_file_path):
            # {"filename": item: "xml": xml}
            registered = cls.is_registered_xml_with_pre(item["xml_with_pre"])
            item.update(registered or {})
            yield item

    @classmethod
    def get_xml_uri(self, v3):
        """
        Retorna XML URI ou None
        """
        return PidProviderXML.get_xml_uri(v3)
