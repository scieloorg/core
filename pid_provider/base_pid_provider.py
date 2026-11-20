import sys

from django.db import transaction
from packtools.sps.pid_provider.xml_sps_lib import XMLWithPre

from core.utils.profiling_tools import (  # ajuste o import conforme sua estrutura
    profile_method,
)
from pid_provider.models import PidProviderXML
from pid_provider.multi_collection import get_xml_collection_acron
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
        collection_acron=None,
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
        collection_acron : str, optional
            Acrônimo da coleção de origem do XML, usado quando o XML não a
            informa (custom-meta), como na coleta de artigos do OPAC
            (task_load_record_from_xml_url); necessário para registrar o pid
            v2 e a versão do XML por coleção (CollectionPidV2) quando o
            periódico está em mais de uma coleção

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

        # identifica a coleção de origem do XML (custom-meta): a do XML
        # prevalece; collection_acron só completa a ausente, como na coleta
        # de artigos do OPAC (task_load_record_from_xml_url), cujo XML pode
        # não informar a coleção. No Upload / migração, a coleção já vem no
        # XML (ver ArticleProc). No Core, o XML pode chegar sem a coleção,
        # por exemplo, enviado (API) por versão do Upload anterior à inserção
        # da coleção no XML: a coleção é identificada pelo PID (contido no
        # pid v2) e pelo acrônimo do periódico; mais de uma coleção
        # identificada é ambíguo e levanta exceção (ver
        # get_xml_collection_acron)
        if not xml_with_pre.collection:
            collection_acron = collection_acron or get_xml_collection_acron(
                xml_with_pre
            )
            if collection_acron:
                xml_with_pre.collection = collection_acron

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
        if self.caller == "core":
            try:
                registered.pop("ppx_id")
            except KeyError:
                pass
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
        collection_acron=None,
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
                    collection_acron=collection_acron,
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
        document_item=None,
        expected_pid_v3=None,
        collection_acron=None,
    ):
        """
        Fornece / Valida PID de um XML disponível por um URI
        
        Obtém o XML, valida o PID v3 informado pela fonte e cria ou atualiza
        PidProviderXML. Falhas são registradas em UnexpectedEvent.

        Returns
        -------
            dict
        """
        try:
            xml_with_pre = list(XMLWithPre.create(uri=xml_uri))[0]
        except Exception as e:
            return self._handle_uri_error(
                e,
                "xml_fetch_failed",
                xml_uri,
                name,
                user,
                origin_date,
                force_update,
                is_published,
                document_item,
                expected_pid_v3,
            )

        if expected_pid_v3 and xml_with_pre.v3 != expected_pid_v3:
            return self._handle_uri_error(
                ValueError(
                    f"PID v3 mismatch: counter_dict={expected_pid_v3}, "
                    f"xml={xml_with_pre.v3}"
                ),
                "pid_v3_mismatch",
                xml_uri,
                name,
                user,
                origin_date,
                force_update,
                is_published,
                document_item,
                expected_pid_v3,
            )

        try:
            with transaction.atomic():
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
                    collection_acron=collection_acron,
                )

                error_msg = response.get("error_msg") or response.get(
                    "error_message"
                )
                if response.get("error_type") or error_msg:
                    raise ValueError(error_msg or response.get("error_type"))
            return response
        except Exception as e:
            return self._handle_uri_error(
                e,
                "pid_provider_xml_failed",
                xml_uri,
                name,
                user,
                origin_date,
                force_update,
                is_published,
                document_item,
                expected_pid_v3,
            )

    def _handle_uri_error(
        self,
        exception,
        stage,
        xml_uri,
        name,
        user,
        origin_date,
        force_update,
        is_published,
        document_item,
        expected_pid_v3,
    ):
        exc_type, exc_value, exc_traceback = sys.exc_info()

        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            item=expected_pid_v3,
            action="PidProvider.provide_pid_for_xml_uri",
            detail={
                "operation": "PidProvider.provide_pid_for_xml_uri",
                "stage": stage,
                "input": dict(
                    xml_uri=xml_uri,
                    user=user.username,
                    name=name,
                    origin_date=origin_date,
                    force_update=force_update,
                    is_published=is_published,
                    document_item=document_item,
                    expected_pid_v3=expected_pid_v3,
                ),
            },
        )

        response = dict(
            error_msg=str(exception),
            error_type=str(type(exception)),
        )
        if exc_value is not None:
            response["exc_value"] = str(exc_value)
        if exc_traceback is not None:
            response["exc_traceback"] = str(exc_traceback)
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
            yield {
                "error_msg": f"Unable to check whether {zip_xml_file_path} is registered {e}",
                "error_type": str(type(e)),
            }
