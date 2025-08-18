import logging
import sys

# from django.utils.translation import gettext as _
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre, get_xml_with_pre

from core.utils.profiling_tools import profile_method  # ajuste o import conforme sua estrutura
from pid_provider.models import PidProviderXML, PidRequest
from tracker.models import UnexpectedEvent


class BasePidProvider:
    def __init__(self):
        self.caller = None

    @profile_method
    def provide_pid_for_xml_with_pre(
        self,
        xml_with_pre,
        name,
        user,
        origin_date=None,
        force_update=None,
        is_published=None,
        origin=None,
        registered_in_core=None,
        caller=None,
        auto_solve_pid_conflict=None,
    ):
        """
        Fornece e valida PIDs para documento XML, retornando dados completos de registro.

        Parameters
        ----------
        xml_with_pre : XMLWithPre
            Objeto XML preprocessado
        name : str
            Nome do arquivo/documento
        user : User
            Usuário responsável pela operação
        origin_date : datetime, optional
            Data de origem do documento
        force_update : bool, optional
            Força atualização mesmo sem alterações
        is_published : bool, optional
            Status de publicação
        origin : str, optional
            Origem do documento
        registered_in_core : bool, optional
            Se já registrado no sistema core
        caller : str, optional
            Identificador do sistema chamador
        auto_solve_pid_conflict : bool, optional
            Resolve conflitos de PID automaticamente

        Returns
        -------
        dict
            Sucesso: {"v3", "v2", "aop_pid", "xml_uri", "article", "created",
                     "updated", "xml_changed", "record_status", "input_data",
                     "xml_adapter_data", "skip_update"*, "xml_with_pre",
                     "apply_xml_changes"*}
            Erro: {"error_type", "error_message", "id", "filename", "error_msg",
                  "xml_with_pre"}

            * Chaves condicionais: skip_update (se atualização pulada),
              apply_xml_changes (se caller="core" e xml_changed=True)
        """
        self.caller = caller

        registered = PidProviderXML.register(
            xml_with_pre,
            name,
            user,
            origin_date=origin_date,
            force_update=force_update,
            is_published=is_published,
            origin=origin,
            registered_in_core=registered_in_core,
            auto_solve_pid_conflict=auto_solve_pid_conflict,  # False = deixar sistema resolver, True = user resolve
        )
        registered["apply_xml_changes"] = self.caller == "core" and registered.get("xml_changed")
        registered["xml_with_pre"] = xml_with_pre
        return registered
    
    @profile_method
    def provide_pid_for_xml_zip(
        self,
        zip_xml_file_path,
        user,
        filename=None,
        origin_date=None,
        force_update=None,
        is_published=None,
        registered_in_core=None,
        caller=None,
        auto_solve_pid_conflict=True,
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
                    registered_in_core=registered_in_core,
                    caller=caller,
                    auto_solve_pid_conflict=auto_solve_pid_conflict,
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
                        auto_solve_pid_conflict=auto_solve_pid_conflict,
                    ),
                },
            )
            yield {
                "error_msg": f"Unable to provide pid for {zip_xml_file_path} {e}",
                "error_type": str(type(e)),
            }

    @profile_method
    def provide_pid_for_xml_uri(
        self,
        xml_uri,
        name,
        user,
        origin_date=None,
        force_update=None,
        is_published=None,
        registered_in_core=None,
        detail=None,
        auto_solve_pid_conflict=None,
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
            detail = dict(
                error_msg=str(e),
                error_type=str(exc_type),
                exc_value=str(exc_value),
                exc_traceback=str(exc_traceback),
            )
            pid_request = PidRequest.register_failure(
                e,
                user=user,
                origin_date=origin_date,
                origin=xml_uri,
                detail=detail,
            )
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
            return detail
        else:
            response = self.provide_pid_for_xml_with_pre(
                xml_with_pre,
                name,
                user,
                origin_date=origin_date,
                force_update=force_update,
                is_published=is_published,
                origin=xml_uri,
                registered_in_core=registered_in_core,
                auto_solve_pid_conflict=auto_solve_pid_conflict,
            )
            if not response.get("error_msg"):
                try:
                    pid_request = PidRequest.cancel_failure(
                        user=user,
                        origin=xml_uri,
                    )
                except Exception:
                    pass
            return response

    @classmethod
    @profile_method
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
        return PidProviderXML.is_registered(xml_with_pre)

    @classmethod
    @profile_method
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
    @profile_method
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
