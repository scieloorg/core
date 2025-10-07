import logging
import sys

from collection.models import Collection
from core.utils.harvesters import AMHarvester
from core.utils import utils
from core.utils.rename_dictionary_keys import rename_issue_dictionary_keys

from issue.models import Issue, AMIssue
from issue.utils.correspondencia import correspondencia_issue
from issue.utils.issue_utils import get_or_create_issue
from journal.models import SciELOJournal
from tracker.models import UnexpectedEvent


def harvest_and_load_issues(user, collection_acron, from_date, until_date, force_update):
    harvester = AMHarvester(
        record_type="issue",
        collection_acron=collection_acron,
        from_date=from_date,
        until_date=until_date,
    )
    for item in harvester.harvest_documents():
        try:
            harvest_and_load_issue(user, item, force_update)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                action="issue.sources.article_meta.create_am_issue_from_am_data",
                detail={"item": item, "user": str(user)}
            )


def harvest_and_load_issue(user, item, force_update):
    try:
        code = item["code"]
        try:
            data_issue = utils.fetch_data(item["url"], json=True, timeout=30, verify=True)
            am_issue = create_am_issue_from_am_data(code, data_issue, user)
        except Exception as e:
            am_issue = create_am_issue_from_am_data(code, item, user)
            return

        issue = create_issue_from_am_data(code, data_issue, user)
        if am_issue and issue:
            issue.legacy_issue.add(am_issue)
            am_issue.status = "done"
            am_issue.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.harvest_and_load_issue",
            detail={"item": item, "user": str(user)}
        )


def create_am_issue_from_am_data(code, data, user):
    """
    Cria ou atualiza Issue a partir dos dados do ArticleMeta.
    
    Args:
        code: PID do issue
        data: Dados do issue (dict com chave 'issue' ou dados diretos)
        user: Usuário responsável
        
    Returns:
        Issue criado/atualizado ou None se falhar
    """
    try:
        # Extrair dados do issue
        status = "pending" if data.get("url") else "wip"
        collection = Collection.objects.get(acron3=data["collection"])
        return AMIssue.create_or_update(
            code, collection, data, user, processing_date=data["processing_date"], status=status,
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.create_am_issue_from_am_data",
            detail={"code": code, "user": str(user)}
        )
        return None


def create_issue_from_am_data(code, data, user):
    """
    Cria ou atualiza Issue a partir dos dados do ArticleMeta.
    
    Args:
        code: PID do issue
        data: Dados do issue (dict com chave 'issue' ou dados diretos)
        user: Usuário responsável
        
    Returns:
        Issue criado/atualizado ou None se falhar
    """
    try:
        # Extrair dados do issue
        journal_pid = data["title"]["code"]
        journal = SciELOJournal.objects.get(
            collection__acron3=data["collection"],
            issn_scielo=journal_pid,
        ).journal

        issue_data = data.get("issue") if "issue" in data else data
        issue_dict = rename_issue_dictionary_keys(
            [issue_data], correspondencia_issue
        )
        # Criar ou atualizar
        return get_or_create_issue(
            journal=journal,
            volume=issue_dict.get("volume"),
            number=issue_dict.get("number"),
            supplement_volume=issue_dict.get("supplement_volume"),
            supplement_number=issue_dict.get("supplement_number"),
            data_iso=issue_dict.get("date_iso"),
            sections_data=issue_dict.get("sections_data"),
            markup_done=issue_dict.get("markup_done"),
            user=user,
        )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.create_issue_from_am_data",
            detail={"code": code, "user": str(user)}
        )
        return None