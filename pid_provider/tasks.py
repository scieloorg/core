import os
import sys
import logging

from django.contrib.auth import get_user_model

from config import celery_app
from core.utils.profiling_tools import (
    profile_function,
)  # ajuste o import conforme sua estrutura
from pid_provider.provider import PidProvider
from pid_provider.models import PidProviderXML
from journal.models import Journal, SciELOJournal
from tracker.models import UnexpectedEvent

# from django.utils.translation import gettext_lazy as _


User = get_user_model()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


@celery_app.task(bind=True)
def task_provide_pid_for_xml_zip(
    self,
    username=None,
    user_id=None,
    zip_filename=None,
):
    return _provide_pid_for_xml_zip(username, user_id, zip_filename)


@profile_function
def _provide_pid_for_xml_zip(
    username=None,
    user_id=None,
    zip_filename=None,
):
    try:
        user = _get_user(None, username=username, user_id=user_id)
        logging.info("Running task_provide_pid_for_xml_zip")
        pp = PidProvider()
        for response in pp.provide_pid_for_xml_zip(
            zip_filename,
            user,
            filename=None,
            origin_date=None,
            force_update=None,
            is_published=None,
            registered_in_core=None,
            caller="core",
        ):
            try:
                response.pop("xml_with_pre")
            except KeyError:
                pass
            return response
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "_provide_pid_for_xml_zip",
                "detail": dict(
                    username=username,
                    user_id=user_id,
                    zip_filename=zip_filename,
                ),
            },
        )
        return {
            "error_msg": f"Unable to provide pid for {zip_filename} {e}",
            "error_type": str(type(e)),
        }


@celery_app.task(bind=True)
def task_delete_provide_pid_tmp_zip(
    self,
    temp_file_path,
):
    if temp_file_path and os.path.exists(temp_file_path):
        os.remove(temp_file_path)


@celery_app.task(bind=True)
def task_fix_pid_provider_xmls_status(
    self,
    username=None,
    user_id=None,
    collection_acron_list=None,
    journal_acron_list=None,
    mark_as_invalid=False,
    mark_as_duplicated=False,
    deduplicate=False,
):
    """
    Marca artigos com diferentes status baseado em filtros de coleções e periódicos.

    Processa artigos aplicando diferentes marcações de status conforme parâmetros.
    Itera diretamente pelos periódicos, usando coleção apenas como filtro.

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        collection_acron_list (list, optional): Lista de acrônimos de coleções para filtrar
        journal_acron_list (list, optional): Lista de acrônimos de periódicos
        mark_as_invalid (bool): Se True, marca artigos como invalid
        mark_as_public (bool): Se True, marca artigos como public
        mark_as_duplicated (bool): Se True, marca artigos como duplicated
        deduplicate (bool): Se True, marca artigos como deduplicated

    Returns:
        dict: Resumo da operação com contadores

    Side Effects:
        - Altera status de artigos no banco
        - Registra UnexpectedEvent em caso de erro
        - Dispara subtarefas para cada periódico

    Examples:
        # Marcar artigos como invalid para coleções específicas
        task_fix_pid_provider_xmls_status.delay(
            collection_acron_list=["scl", "mex"],
            journal_acron_list=["abc", "xyz"],
            mark_as_invalid=True
        )
        
        # Marcar artigos como public e deduplicated
        task_fix_pid_provider_xmls_status.delay(
            journal_acron_list=["abc"],
            mark_as_public=True,
            deduplicate=True
        )
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        
        # Validação: ao menos uma operação deve ser especificada
        operations = {
            "invalid": mark_as_invalid,
            "duplicated": mark_as_duplicated,
            "deduplicated": deduplicate,
        }
        
        if not any(operations.values()):
            raise ValueError("At least one marking operation must be specified")
        
        # Construir filtros para os periódicos
        journal_filters = {}
        
        # Filtro por coleção (através do relacionamento)
        if collection_acron_list:
            journal_filters['collection_acron3__in'] = collection_acron_list
        
        # Filtro por periódico
        if journal_acron_list:
            journal_filters['journal_acron__in'] = journal_acron_list
        
        # Iterar pelos periódicos e disparar subtarefas
        journals_processed = 0
        for journal_id in SciELOJournal.objects.filter(**journal_filters).values_list('journal__id', flat=True).distinct():
            task_fix_journal_pid_provider_xmls_status.apply_async(
                kwargs={
                    "username": username,
                    "user_id": user_id,
                    "journal_id": journal_id,
                    "mark_as_invalid": mark_as_invalid,
                    "mark_as_duplicated": mark_as_duplicated,
                    "deduplicate": deduplicate,
                }
            )
            journals_processed += 1
        
        return {
            "status": "success",
            "journals_processed": journals_processed,
            "operations": {k: v for k, v in operations.items() if v},
            "filters": {
                "collections": collection_acron_list,
                "journals": journal_acron_list
            }
        }
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_fix_pid_provider_xmls_status",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "operations": {
                    "mark_as_invalid": mark_as_invalid,
                    "mark_as_duplicated": mark_as_duplicated,
                    "deduplicate": deduplicate,
                }
            },
        )
        raise


@celery_app.task(bind=True)
def task_fix_journal_pid_provider_xmls_status(
    self,
    username=None,
    user_id=None,
    journal_id=None,
    journal_acron=None,
    collection_acron=None,
    mark_as_invalid=False,
    mark_as_duplicated=False,
    deduplicate=False,
):
    """
    Marca artigos com diferentes status para um periódico específico.

    Processa artigos do periódico aplicando as marcações de status especificadas.
    Cada operação de marcação é executada independentemente se habilitada.

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        journal_id (int, optional): ID do periódico (preferencial por performance)
        journal_acron (str, optional): Acrônimo do periódico (alternativa ao journal_id)
        mark_as_invalid (bool): Se True, marca artigos sem registro ativo como invalid
        mark_as_public (bool): Se True, marca artigos como public
        mark_as_duplicated (bool): Se True, marca artigos como duplicated
        deduplicate (bool): Se True, marca artigos como deduplicated

    Returns:
        dict: Resumo das operações realizadas

    Raises:
        ValueError: Se nem journal_id nem journal_acron forem fornecidos

    Side Effects:
        - Altera status de artigos no banco
        - Registra UnexpectedEvent em caso de erro
        - Pode executar múltiplas operações de marcação em sequência

    """
    try:
        # Validar que ao menos um identificador foi fornecido
        if not journal_id and not journal_acron:
            raise ValueError("Either journal_id or journal_acron must be provided")
        
        user = _get_user(self.request, username=username, user_id=user_id)

        journal = None
        if journal_id:
            journal = Journal.objects.filter(id=journal_id).first()
        elif journal_acron and collection_acron:
            journal = SciELOJournal.objects.filter(
                journal_acron=journal_acron, collection__acron3=collection_acron
            ).first().journal
        if not journal:
            raise ValueError("Journal not found with provided identifier")
        
        if mark_as_invalid:
            PidProviderXML.mark_items_as_invalid(journal.issns)
    
        if mark_as_duplicated:
            PidProviderXML.mark_items_as_duplicated(journal.issns)

        if deduplicate:
            PidProviderXML.deduplicate_items(user, journal.issns)

        return {
            "status": "success",
            "journal_id": journal.id,
            "journal_acron": journal_acron,
            "collection_acron": collection_acron,
            "operations_performed": {
                "mark_as_invalid": mark_as_invalid,
                "mark_as_duplicated": mark_as_duplicated,
                "deduplicate": deduplicate,
            }
        }
  
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_fix_journal_pid_provider_xmls_status",
                "journal_id": journal_id,
                "journal_acron": journal_acron,
                "collection_acron": collection_acron,
                "operations": {
                    "mark_as_invalid": mark_as_invalid,
                    "mark_as_duplicated": mark_as_duplicated,
                    "deduplicate": deduplicate,
                }
            },
        )
        raise