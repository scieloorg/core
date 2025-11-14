import logging
import sys

from collection.models import Collection
from core.utils.harvesters import AMHarvester
from core.utils import utils
from core.utils.rename_dictionary_keys import rename_issue_dictionary_keys

from issue.models import Issue, AMIssue
from issue.articlemeta.correspondencia import correspondencia_issue
from issue.articlemeta.issue_utils import get_or_create_issue
from journal.models import SciELOJournal
from tracker.models import UnexpectedEvent


def harvest_and_load_issues(user, collection_acron, from_date, until_date, force_update):
    try:
        harvester = AMHarvester(
            record_type="issue",
            collection_acron=collection_acron,
            from_date=from_date,
            until_date=until_date,
        )
        collection = Collection.objects.get(acron3=collection_acron)
        for item in harvester.harvest_documents():
            harvest_and_load_issue(user, collection, item, force_update)

        for am_issue in AMIssue.objects.filter(
            collection__acron3=collection_acron,
            status__in=["todo", "pending"],
        ):
            create_issue_from_am_issue(user, am_issue)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.harvest_and_load_issues",
            detail={
                "collection_acron": collection_acron,
                "from_date": from_date,
                "until_date": until_date,
                "force_update": force_update
            }
        )


def harvest_and_load_issue(user, collection, item, force_update):
    try:
        pid = item["code"]
        url = item["url"]
        processing_date = item["processing_date"]
        am_issue = load_am_issue(user, collection, pid, url, processing_date, force_update)
        if not am_issue:
            raise ValueError(f"Unable to create am_issue for {collection} {pid} {url}")
        create_issue_from_am_issue(user, am_issue)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.harvest_and_load_issue",
            detail={"item": item, "force_update": force_update}
        )


def load_am_issue(user, collection, pid, url, processing_date, force_update):
    try:
        try:
            data_issue = utils.fetch_data(url, json=True, timeout=30, verify=True)
            status = "pending"
        except Exception as e:
            data_issue = None
            status = "todo"
        
        return AMIssue.create_or_update(
            pid=pid,
            collection=collection,
            data=data_issue,
            user=user,
            url=url,
            status=status,
            processing_date=processing_date,
            force_update=force_update,
        )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.load_am_issue",
            detail={"collection": collection, "pid": pid, "force_update": force_update}
        )


def complete_am_issue(user, am_issue):
    try:
        url = am_issue.url
        if not url:
            url = (am_issue.data or {}).get("url")
            am_issue.url = url
        if not url:
            raise ValueError(f"Unable to get data from {am_issue}: URL is missing")
        am_issue.data = utils.fetch_data(url, json=True, timeout=30, verify=True)
        am_issue.status = "pending"
        am_issue.updated_by = user
        am_issue.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.complete_am_issue",
            detail={"am_issue": str(am_issue)}
        )


def create_issue_from_am_issue(user, am_issue):
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
        if not am_issue.data:
            complete_am_issue(user, am_issue)
            
        data = am_issue.data
        if not data:
            raise ValueError(f"Unable to create issue for {am_issue}") 

        journal_pid = data["title"]["code"]
        scielo_journal = SciELOJournal.objects.get(
            collection__acron3=data["collection"],
            issn_scielo=journal_pid,
        )
        journal = scielo_journal.journal

        issue_data = data.get("issue") if "issue" in data else data
        issue_dict = rename_issue_dictionary_keys(
            [issue_data], correspondencia_issue
        )
        # Criar ou atualizar
        issue = get_or_create_issue(
            journal=journal,
            volume=issue_dict.get("volume"),
            number=issue_dict.get("number"),
            supplement_volume=issue_dict.get("supplement_volume"),
            supplement_number=issue_dict.get("supplement_number"),
            data_iso=issue_dict.get("date_iso"),
            sections_data=issue_dict.get("sections_data"),
            markup_done=issue_dict.get("markup_done"),
            user=user,
            collection=scielo_journal.collection,
        )
        if issue:
            issue.legacy_issue.add(am_issue)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.create_issue_from_am_issue",
            detail={"am_issue": str(am_issue), "user": str(user)}
        )
        return None