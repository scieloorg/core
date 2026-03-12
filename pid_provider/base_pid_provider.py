import sys
import traceback

# from django.utils.translation import gettext_lazy as _
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre, get_xml_with_pre

from core.utils.profiling_tools import (  # ajuste o import conforme sua estrutura
    profile_method,
)
from pid_provider.models import PidProviderXML, XMLURL
from tracker.models import UnexpectedEvent


def _truncate_traceback(tb_str, max_length=255):
    """
    Truncate traceback string to fit in max_length.
    If longer than max_length, keep start and end portions.
    
    Args:
        tb_str: Traceback string (can be None)
        max_length: Maximum length (default 255)
        
    Returns:
        Truncated traceback string or None
    """
    if tb_str is None:
        return None
        
    if len(tb_str) <= max_length:
        return tb_str
    
    # Keep beginning and end with "..." in the middle
    keep_chars = (max_length - 5) // 2  # Reserve 5 chars for " ... "
    return tb_str[:keep_chars] + " ... " + tb_str[-keep_chars:]


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
            registered_in_core=registered_in_core or self.caller == "core",
            auto_solve_pid_conflict=auto_solve_pid_conflict,  # False = deixar sistema resolver, True = user resolve
        )
        registered["apply_xml_changes"] = self.caller == "core" and registered.get(
            "xml_changed"
        )
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
        
        This method handles three types of exceptions:
        a) Failure to obtain XML - registers only URL, status, and PID in XMLURL
        b) Successfully obtain XML but fail to create PidProviderXML record - 
           registers everything + saves compressed XML content
        c) Unexpected errors - logs in UnexpectedEvent

        Returns
        -------
            dict
        """
        # a) Try to obtain XML from URI
        try:
            xml_with_pre = list(XMLWithPre.create(uri=xml_uri))[0]
        except Exception as e:
            return self._handle_xml_fetch_failure(e, xml_uri, name, user, origin_date, force_update, is_published)
        
        # b) Try to create PidProviderXML record
        try:
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
            
            # Handle response based on success or failure
            if response.get("error_type") or response.get("error_message"):
                self._handle_pid_provider_failure(response, xml_with_pre, xml_uri, name, user, origin_date, force_update, is_published)
            else:
                self._register_success(xml_with_pre, xml_uri, name, user, response)
            
            return response
            
        except Exception as e:
            return self._handle_unexpected_error(e, xml_uri, name, user, origin_date, force_update, is_published)

    def _handle_xml_fetch_failure(self, exception, xml_uri, name, user, origin_date, force_update, is_published):
        """Handle exception type a) - Failure to obtain XML"""
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        # Get traceback and truncate if needed
        tb_str = traceback.format_exc()
        truncated_tb = _truncate_traceback(tb_str)
        
        # Store exception in XMLURL instead of UnexpectedEvent
        XMLURL.create_or_update(
            user=user,
            url=xml_uri,
            status="xml_fetch_failed",
            pid=None,
            exceptions=truncated_tb,
        )
        
        return dict(
            error_msg=str(exception),
            error_type=str(exc_type),
            exc_value=str(exc_value),
            exc_traceback=str(exc_traceback),
        )

    def _handle_pid_provider_failure(self, response, xml_with_pre, xml_uri, name, user, origin_date, force_update, is_published):
        """Handle exception type b) - XML obtained but PidProviderXML creation failed"""
        # Format error information from response (not from an exception context)
        error_msg = response.get("error_message", "Unknown error")
        error_type = response.get("error_type", "Unknown")
        error_info = f"{error_type}: {error_msg}"
        truncated_error = _truncate_traceback(error_info)
        
        # Create or update XMLURL with exception info and save zipfile
        xmlurl_obj = XMLURL.create_or_update(
            user=user,
            url=xml_uri,
            status="pid_provider_xml_failed",
            pid=response.get("id") or response.get("v3"),
            exceptions=truncated_error,
        )
        # Use XMLWithPre.tostring() method
        xmlurl_obj.save_file(xml_with_pre.tostring(), filename=name or 'content.xml')

    def _register_success(self, xml_with_pre, xml_uri, name, user, response):
        """Register successful XML processing in XMLURL"""
        xmlurl_obj = XMLURL.create_or_update(
            user=user,
            url=xml_uri,
            status="success",
            pid=response.get("v3"),
        )
        # Use XMLWithPre.tostring() method
        xmlurl_obj.save_file(xml_with_pre.tostring(), filename=name or 'content.xml')

    def _handle_unexpected_error(self, exception, xml_uri, name, user, origin_date, force_update, is_published):
        """Handle exception type c) - Unexpected error during processing"""
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "operation": "PidProvider.provide_pid_for_xml_uri",
                "exception_type": "unexpected_error",
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
        
        return dict(
            error_msg=str(exception),
            error_type=str(exc_type),
            exc_value=str(exc_value),
            exc_traceback=str(exc_traceback),
        )

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
