import logging
import sys

# from django.utils.translation import gettext as _
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre

from pid_provider.models import PidProviderXML
from tracker.models import UnexpectedEvent

LOGGER = logging.getLogger(__name__)
LOGGER_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class BasePidProvider:

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
                yield self.provide_pid_for_xml_with_pre(
                    xml_with_pre,
                    xml_with_pre.filename,
                    user,
                    origin_date=origin_date,
                    force_update=force_update,
                    is_published=is_published,
                    origin=zip_xml_file_path,
                )
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "PidProvider.provide_pid_for_xml_zip",
                    "input": dict(
                        zip_xml_file_path=zip_xml_file_path,
                        user=user.username,
                        filename=filename,
                        origin_date=origin_date,
                        force_update=force_update,
                        is_published=is_published,
                    ),
                },
            )
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
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "PidProvider.provide_pid_for_xml_uri",
                    "input": dict(
                        xml_uri=xml_uri,
                        user=user.username,
                        name=name,
                        origin_date=origin_date,
                        force_update=force_update,
                        is_published=is_published,
                    ),
                },
            )
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
                origin=xml_uri,
            )

    @classmethod
    def is_registered_xml_with_pre(cls, xml_with_pre, origin):
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
        return PidProviderXML.get_registered(xml_with_pre, origin)

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
        try:
            for xml_with_pre in XMLWithPre.create(uri=xml_uri):
                return cls.is_registered_xml_with_pre(xml_with_pre, xml_uri)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "PidProvider.is_registered_xml_uri",
                    "input": dict(
                        xml_uri=xml_uri,
                    ),
                },
            )
            return {
                "error_msg": f"Unable to check whether {xml_uri} is registered {e}",
                "error_type": str(type(e)),
            }

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
        try:
            for xml_with_pre in XMLWithPre.create(path=zip_xml_file_path):
                yield cls.is_registered_xml_with_pre(xml_with_pre, zip_xml_file_path)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "PidProvider.is_registered_xml_zip",
                    "input": dict(
                        zip_xml_file_path=zip_xml_file_path,
                    ),
                },
            )
            return {
                "error_msg": f"Unable to check whether {zip_xml_file_path} is registered {e}",
                "error_type": str(type(e)),
            }

    def provide_pid_for_xml_with_pre(
        self,
        xml_with_pre,
        name,
        user,
        origin_date=None,
        force_update=None,
        is_published=None,
        origin=None,
    ):
        """
        Recebe um xml_with_pre para solicitar o PID da versão 3
        para o Pid Provider

        Se o xml_with_pre já está registrado local e remotamente,
        apenas retorna os dados registrados
        {
            'registered': {...},
            'required_local_registration': False,
            'required_remote_registration': False,
        }

        Caso contrário, solicita PID versão 3 para o Pid Provider e
        armazena o resultado
        """
        v3 = xml_with_pre.v3
        response = self.pre_registration(xml_with_pre, name)
        if response.get("required_local_registration"):
            registered = PidProviderXML.register(
                xml_with_pre,
                name,
                user,
                origin_date=origin_date,
                force_update=force_update,
                is_published=is_published,
                origin=origin,
            )
        else:
            registered = response.get("registered")

        # registered["xml_changed"] = v3 != xml_with_pre.v3
        # registered["xml_uri"] = response.get("xml_uri")
        logging.info(f"PidProvider.provide_pid_for_xml_with_pre: registered={registered}")

        response.update(registered)
        return response


class PidProvider(BasePidProvider):
    """
    Recebe XML para validar ou atribuir o ID do tipo v3
    """

    def __init__(self):
        pass

    def provide_pid_for_xml_with_pre(
        self,
        xml_with_pre,
        name,
        user,
        origin_date=None,
        force_update=None,
        is_published=None,
        origin=None,
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
            origin=origin,
        )
        logging.info("")
        logging.info(f"provide pid for {origin} result: {registered}")
        return registered
