import logging
import sys

from django.contrib.auth import get_user_model

from config import celery_app
from core.utils.utils import _get_user
from collection.models import Collection
from issue import controller
from issue.articlemeta.harvester import harvest_and_load_issues
from tracker.models import UnexpectedEvent

User = get_user_model()

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def load_issue_from_article_meta(
    self,
    user_id=None, username=None, collection_acron=None, from_date=None, until_date=None, force_update=None,
):
    try:
        user = _get_user(request=self.request, user_id=user_id, username=username)

        for acron3 in Collection.get_acronyms(collection_acron):
            harvest_and_load_issues(
                user=user,
                collection_acron=acron3,
                from_date=from_date,
                until_date=until_date,
                force_update=force_update,
            )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.tasks.load_issue_from_article_meta",
            detail={"collection_acron": collection_acron, "from_date": from_date, "until_date": until_date, "force_update": force_update}
        )


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