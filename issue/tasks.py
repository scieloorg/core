import logging
import sys

from django.contrib.auth import get_user_model

from config import celery_app
from core.utils.utils import _get_user
from collection.models import Collection
from issue import controller
from issue.articlemeta.loader import harvest_issue_identifiers, harvest_and_load_issue
from issue.articlemeta.loader import create_issue_from_am_issue, load_issue_sections, load_issue_titles, load_bibliographic_strips, get_issue_data_from_am_issue
from issue.models import AMIssue
from tracker.models import UnexpectedEvent


User = get_user_model()

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def load_issue_from_article_meta(
    self,
    user_id=None,
    username=None,
    collection_acron=None,
    from_date=None,
    until_date=None,
    force_update=None,
    timeout=30,
):
    """
    Carrega issues do ArticleMeta para collections específicas.
    
    Args:
        user_id: ID do usuário
        username: Nome do usuário
        collection_acron: Acrônimo da collection ou lista de acrônimos
        from_date: Data inicial (YYYY-MM-DD)
        until_date: Data final (YYYY-MM-DD)
        force_update: Forçar atualização de registros existentes
        timeout: Timeout para requisições HTTP
    """
    try:
        user = _get_user(request=self.request, user_id=user_id, username=username)

        # Obter lista de acrônimos das collections
        collection_acronyms = Collection.get_acronyms(collection_acron)
        
        for acron3 in collection_acronyms:
            try:
                logger.info(f"Harvesting issues for collection {acron3}")
                
                # Coletar identificadores de issues
                for issue_identifier in harvest_issue_identifiers(
                    acron3, from_date, until_date, force_update, timeout
                ):
                    try:
                        logger.info(f"Scheduling load for issue {issue_identifier.get('code')} in collection {acron3}")
                        
                        # Agendar task para carregar issue específico
                        task_harvest_and_load_issue.delay(
                            user_id=user.id,
                            collection_acron=acron3,
                            issue_identifier=issue_identifier,
                            force_update=force_update,
                            timeout=timeout,
                        )
                    except Exception as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        UnexpectedEvent.create(
                            exception=e,
                            exc_traceback=exc_traceback,
                            action="issue.tasks.load_issue_from_article_meta.schedule_task_load_issue",
                            detail={
                                "collection_acron": acron3,
                                "issue_identifier": issue_identifier,
                                "force_update": force_update,
                            }
                        )
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    action="issue.tasks.load_issue_from_article_meta.process_collection",
                    detail={
                        "collection_acron": acron3,
                        "from_date": from_date,
                        "until_date": until_date,
                        "force_update": force_update,
                    }
                )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.tasks.load_issue_from_article_meta",
            detail={
                "collection_acron": collection_acron,
                "from_date": from_date,
                "until_date": until_date,
                "force_update": force_update
            }
        )


@celery_app.task(bind=True)
def task_harvest_and_load_issue(
    self,
    user_id=None,
    username=None,
    collection_acron=None,
    issue_identifier=None,
    force_update=None,
    timeout=30,
):
    """
    Carrega um issue específico do ArticleMeta.
    
    Args:
        user_id: ID do usuário
        username: Nome do usuário  
        collection_acron: Acrônimo da collection
        issue_identifier: Dados do identificador do issue
        force_update: Forçar atualização de registros existentes
        timeout: Timeout para requisições HTTP
    """
    try:
        user = _get_user(request=self.request, user_id=user_id, username=username)
        
        # Validações
        if not issue_identifier:
            raise ValueError("issue_identifier is required")
        if not collection_acron:
            raise ValueError("collection_acron is required")
        
        # Extrair dados do identificador
        url = issue_identifier.get("url")
        code = issue_identifier.get("code") 
        processing_date = issue_identifier.get("processing_date")
        
        if not url:
            raise ValueError("URL is required in issue_identifier")
        if not code:
            raise ValueError("Code is required in issue_identifier")
        
        logger.info(f"Loading issue {code} from {url}")
        
        # Carregar issue
        issue = harvest_and_load_issue(
            user=user,
            url=url,
            code=code,
            collection_acron=collection_acron,
            processing_date=processing_date,
            force_update=force_update,
            timeout=timeout,
        )
        
        if issue:
            logger.info(f"Successfully loaded issue {issue}")
            return issue.id
        else:
            logger.warning(f"Failed to load issue {code} from {url}")
            
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.tasks.task_harvest_and_load_issue",
            detail={
                "collection_acron": collection_acron,
                "issue_identifier": issue_identifier,
                "force_update": force_update,
            }
        )
        # Re-raise para que Celery marque a task como falhada
        raise


@celery_app.task(bind=True, name="task_export_issues_to_articlemeta")
def task_export_issues_to_articlemeta(
    self,
    collection_acron_list=None,
    journal_acron_list=None,
    publication_year=None,
    volume=None,
    number=None,
    supplement=None,
    force_update=False,
    user_id=None,
    username=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
):
    """
    Export issues to ArticleMeta Database with flexible filtering.
    
    Args:
        collection_acron_list: List of collections to export
        journal_acron_list: Filter by journal acronyms
        publication_year: Filter by publication year
        volume: Filter by volume number
        number: Filter by issue number
        supplement: Filter by supplement
        force_update: Force update existing records
        user_id: User ID for authentication
        username: Username for authentication
        from_date: Start date for filtering
        until_date: End date for filtering
        days_to_go_back: Number of days to go back from current date
    
    Returns:
        dict: Result of bulk export operation
    
    Raises:
        Exception: Any unexpected error during export
    """
    try:
        user = _get_user(request=self.request, user_id=user_id, username=username)
        
        result = controller.bulk_export_issues_to_articlemeta(
            user,
            collection_acron_list,
            journal_acron_list,
            publication_year,
            volume,
            number,
            supplement,
            from_date,
            until_date,
            days_to_go_back,
            force_update,
        )
        
        return result
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_export_issues_to_articlemeta",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "publication_year": publication_year,
                "volume": volume,
                "number": number,
                "supplement": supplement,
                "force_update": force_update,
                "from_date": str(from_date) if from_date else None,
                "until_date": str(until_date) if until_date else None,
                "days_to_go_back": days_to_go_back,
                "user_id": user_id,
                "username": username,
                "task_id": self.request.id if hasattr(self.request, 'id') else None,
            },
        )
        
        # Re-raise para que o Celery possa tratar a exceção adequadamente
        raise


@celery_app.task(bind=True, name="task_export_issue_to_articlemeta")
def task_export_issue_to_articlemeta(
    self,
    collection_acron,
    journal_acron,
    publication_year=None,
    volume=None,
    number=None,
    supplement=None,
    force_update=None,
    user_id=None,
    username=None,
):
    """
    Export a single issue to ArticleMeta Database.
    
    Args:
        collection_acron: Collection acronym (required)
        journal_acron: Journal acronym (required)
        publication_year: Publication year of the issue
        volume: Volume number
        number: Issue number
        supplement: Supplement identifier
        force_update: Force update existing records
        user_id: User ID for authentication
        username: Username for authentication
    
    Returns:
        dict: Result of bulk export operation
    
    Raises:
        ValueError: If required parameters are missing
        Exception: Any unexpected error during export
    """
    try:
        # Validações básicas de parâmetros obrigatórios
        if not collection_acron:
            raise ValueError("collection_acron is required")
        if not journal_acron:
            raise ValueError("journal_acron is required")
        
        # Validação adicional: pelo menos um identificador do issue deve ser fornecido
        if not any([publication_year, volume, number, supplement]):
            raise ValueError(
                "At least one issue identifier is required: "
                "publication_year, volume, number, or supplement"
            )
        
        user = _get_user(request=self.request, user_id=user_id, username=username)
        
        result = controller.bulk_export_issues_to_articlemeta(
            user,
            collection_acron_list=[collection_acron],
            journal_acron_list=[journal_acron],
            publication_year=publication_year,
            volume=volume,
            number=number,
            supplement=supplement,
            force_update=force_update,
        )
        
        return result    
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_export_issue_to_articlemeta",
                "collection_acron": collection_acron,
                "journal_acron": journal_acron,
                "publication_year": publication_year,
                "volume": volume,
                "number": number,
                "supplement": supplement,
                "force_update": force_update,
                "user_id": user_id,
                "username": username,
                "task_id": self.request.id if hasattr(self.request, 'id') else None,
                "error_type": "unexpected_error",
            },
        )
        
        # Re-raise para que o Celery possa tratar a exceção adequadamente
        raise


@celery_app.task(bind=True, name="task_update_issues_from_amissue")
def task_update_issues_from_amissue(
    self,
    user_id=None,
    username=None,
    collection_acron=None,
    journal_pid=None,
    issue_status=None,
    processing_date_from=None,
    processing_date_until=None,
    year=None,
    volume=None,
    number=None,
    supplement=None,
    force_update=False,
    only_without_new_record=False,
):
    """
    Atualiza Issues a partir de registros AMIssue com filtros específicos.
    
    Args:
        user_id: ID do usuário
        username: Nome do usuário
        collection_acron: Acrônimo da collection para filtrar
        journal_pid: PID do journal para filtrar
        issue_status: Status do AMIssue ('pending', 'todo', 'done')
        processing_date_from: Data inicial de processamento (YYYY-MM-DD)
        processing_date_until: Data final de processamento (YYYY-MM-DD)
        year: Ano de publicação para filtrar Issues
        volume: Volume para filtrar Issues
        number: Número para filtrar Issues
        supplement: Suplemento para filtrar Issues
        force_update: Forçar atualização de Issues existentes
        only_without_new_record: Processar apenas AMIssue sem new_record associado
    
    Returns:
        dict: Resultado da operação com estatísticas
    """
    try:
        user = _get_user(request=self.request, user_id=user_id, username=username)
        
        try:
            # Limpar AMIssue órfãos (sem data e sem URL)
            AMIssue.objects.filter(data__isnull=True, url__isnull=True).delete()
        except Exception:
            pass

        # Construir filtros para AMIssue
        filters = {}
        
        if collection_acron:
            try:
                collection = Collection.objects.get(acron3=collection_acron)
                filters['collection'] = collection
            except Collection.DoesNotExist:
                raise ValueError(f"Collection with acron3 '{collection_acron}' not found")
        
        if issue_status:
            if issue_status not in ['pending', 'todo', 'done']:
                raise ValueError("issue_status must be one of: 'pending', 'todo', 'done'")
            filters['status'] = issue_status

        if processing_date_from:
            filters['processing_date__gte'] = processing_date_from
        
        if processing_date_until:
            filters['processing_date__lte'] = processing_date_until
            
        if only_without_new_record:
            filters['new_record__isnull'] = True
        
        # Filtros adicionais baseados no PID (que contém informações do issue)
        if journal_pid:
            filters['pid__icontains'] = journal_pid
        
        if not force_update:
            if not filters:
                # Garantir que algum filtro exista
                filters["data__isnull"] = True

        # Obter queryset de AMIssue
        am_issues = AMIssue.objects.filter(**filters)
        
        if not am_issues.exists():
            result = {
                "processed": 0,
                "updated": 0,
                "created": 0,
                "errors": 0,
                "message": "No AMIssue records found with the specified filters"
            }
            return result
        
        # Estatísticas de processamento
        stats = {
            "processed": 0,
            "updated": 0,
            "created": 0,
            "errors": 0,
            "error_details": []
        }
        
        logger.info(f"Found {am_issues.count()} AMIssue records to process")
        
        for am_issue in am_issues.iterator():
            try:
                stats["processed"] += 1
                
                # Extrair dados do AMIssue para aplicar filtros adicionais
                issue_data = get_issue_data_from_am_issue(am_issue, user)
                if not issue_data:
                    stats["errors"] += 1
                    stats["error_details"].append({
                        "am_issue_id": am_issue.id,
                        "pid": am_issue.pid,
                        "error": "Unable to extract issue data from AMIssue"
                    })
                    continue
                
                # Aplicar filtros específicos do Issue
                should_skip = False
                
                if year and issue_data.get("year") != year:
                    should_skip = True
                if volume and issue_data.get("volume") != volume:
                    should_skip = True
                if number and issue_data.get("number") != number:
                    should_skip = True
                if supplement and issue_data.get("supplement") != supplement:
                    should_skip = True
                
                if should_skip:
                    continue
                
                # Verificar se já existe Issue para este AMIssue
                existing_issue = am_issue.new_record
                
                if existing_issue and not force_update:
                    # Issue já existe e não estamos forçando update
                    continue
                
                if existing_issue and force_update:
                    # Atualizar Issue existente
                    logger.info(f"Updating existing Issue {existing_issue.id} from AMIssue {am_issue.id}")
                    
                    # Recarregar dados do AMIssue no Issue
                    load_issue_sections(user, existing_issue, am_issue, issue_data, collection=am_issue.collection)
                    load_issue_titles(user, existing_issue, am_issue, issue_data)
                    load_bibliographic_strips(user, existing_issue, am_issue, issue_data)
                    
                    stats["updated"] += 1
                    
                else:
                    # Criar novo Issue
                    logger.info(f"Creating new Issue from AMIssue {am_issue.id}")
                    
                    issue = create_issue_from_am_issue(user, am_issue)
                    if issue:
                        stats["created"] += 1
                    else:
                        stats["errors"] += 1
                        stats["error_details"].append({
                            "am_issue_id": am_issue.id,
                            "pid": am_issue.pid,
                            "error": "Failed to create Issue from AMIssue"
                        })
                
            except Exception as e:
                stats["errors"] += 1
                stats["error_details"].append({
                    "am_issue_id": am_issue.id,
                    "pid": getattr(am_issue, 'pid', None),
                    "error": str(e)
                })
                
                # Log individual errors but continue processing
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    action="issue.tasks.task_update_issues_from_amissue.process_am_issue",
                    detail={
                        "am_issue_id": am_issue.id,
                        "pid": getattr(am_issue, 'pid', None),
                        "collection_acron": collection_acron,
                        "force_update": force_update,
                    }
                )
                continue
        
        # Log do resultado final
        logger.info(f"Task completed. Processed: {stats['processed']}, "
                   f"Created: {stats['created']}, Updated: {stats['updated']}, "
                   f"Errors: {stats['errors']}")
        
        return stats
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.tasks.task_update_issues_from_amissue",
            detail={
                "collection_acron": collection_acron,
                "journal_pid": journal_pid,
                "issue_status": issue_status,
                "processing_date_from": processing_date_from,
                "processing_date_until": processing_date_until,
                "year": year,
                "volume": volume,
                "number": number,
                "supplement": supplement,
                "force_update": force_update,
                "only_without_new_record": only_without_new_record,
                "user_id": user_id,
                "username": username,
                "task_id": self.request.id if hasattr(self.request, 'id') else None,
            },
        )
        
        # Re-raise para que o Celery possa tratar a exceção adequadamente
        raise