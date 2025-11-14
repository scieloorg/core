import logging
import sys

from collection.models import Collection
from core.utils.harvesters import AMHarvester
from core.utils import utils
from core.utils.rename_dictionary_keys import rename_issue_dictionary_keys

from issue.models import AMIssue, Issue
from issue.articlemeta.correspondencia import correspondencia_issue
from issue.articlemeta.issue_utils import extract_data_from_harvested_data
from journal.models import SciELOJournal
from tracker.models import UnexpectedEvent


def harvest_issue_identifiers(
    collection_acron, from_date, until_date, force_update, timeout=30
):
    try:
        harvester = AMHarvester(
            record_type="issue",
            collection_acron=collection_acron,
            from_date=from_date,
            until_date=until_date,
        )
        yield from harvester.harvest_documents()

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.harvester.harvest_and_load_am_issues",
            detail={
                "collection_acron": collection_acron,
                "from_date": from_date,
                "until_date": until_date,
                "force_update": force_update,
            },
        )


def harvest_and_load_issue(user, url, code, collection_acron, processing_date, force_update, timeout=30):
    if not url:
        raise ValueError("URL is required to harvest and load issue")

    if not code:
        raise ValueError("Code is required to harvest and load issue")

    if not collection_acron:
        raise ValueError("Collection acronym is required to harvest and load issue")
    
    harvested_data = harvest_issue_data(url, timeout=timeout)
    am_issue = load_am_issue(
        user,
        Collection.objects.get(acron3=collection_acron),
        url,
        code,
        processing_date,
        harvested_data,
        force_update=force_update,
        timeout=timeout,
    )
    if not am_issue:
        raise ValueError(f"Unable to create am_issue for {url}")
    return create_issue_from_am_issue(user, am_issue)


def harvest_issue_data(url, timeout=30):
    try:
        item = {}
        item["data"] = utils.fetch_data(url, json=True, timeout=timeout, verify=True)
        item["status"] = "pending"
        return item
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.harvester.harvest_issue_data",
            detail={"url": url},
        )
        item["data"] = None
        item["status"] = "todo"
        return item


def load_am_issue(
    user,
    collection,
    url,
    pid,
    processing_date,
    harvested_data,
    force_update,
    do_harvesting=False,
    timeout=30,
):
    try:
        if not url:
            raise ValueError("URL is required to load AMIssue")
        
        harvested_data = {}
        if do_harvesting or not harvested_data:
            harvested_data = harvest_issue_data(url, timeout=timeout)

        return AMIssue.create_or_update(
            pid=pid,
            collection=collection,
            data=harvested_data.get("data"),
            user=user,
            url=url,
            status=harvested_data.get("status"),
            processing_date=processing_date,
            force_update=force_update,
        )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.harvester.load_am_issue",
            detail={
                "collection": collection.acron3,
                "url": url,
                "force_update": force_update,
            },
        )


def complete_am_issue(user, am_issue):
    try:
        harvested_data = harvest_issue_data(am_issue.url)
        am_issue.status = harvested_data.get("status")
        am_issue.data = harvested_data.get("data")
        am_issue.updated_by = user
        am_issue.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.complete_am_issue",
            detail={"am_issue": str(am_issue)},
        )


def get_issue_data_from_am_issue(am_issue, user=None):
    """
    Extrai e ajusta dados do AMIssue para criação de Issue.

    Args:
        am_issue: Instância de AMIssue

    Returns:
        Dict com dados ajustados para Issue ou None se falhar
    """
    try:
        # Extrair dados do issue
        if not am_issue:
            raise ValueError("am_issue is required")
        if not am_issue.data:
            if user:
                complete_am_issue(user, am_issue)

        am_data = am_issue.data
        if not am_data:
            raise ValueError(f"Unable to get issue data from {am_issue}")

        journal_pid = am_data["title"]["code"]
        if not journal_pid:
            raise ValueError(f"Unable to get journal_pid from {am_issue}")

        issue_data = am_data["issue"]
        if not issue_data:
            raise ValueError(f"Unable to get issue data from {am_issue}")

        scielo_journal = SciELOJournal.objects.get(
            collection=am_issue.collection,
            issn_scielo=journal_pid,
        )
        issue_dict = rename_issue_dictionary_keys([issue_data], correspondencia_issue)

        # Retornar dados ajustados para Issue
        extracted_data = extract_data_from_harvested_data(issue_dict, am_issue.pid)
        extracted_data["journal"] = scielo_journal.journal
        return extracted_data
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.harvester.get_issue_data_from_am_issue",
            detail={"am_issue": str(am_issue)},
        )
        return None


def create_issue_from_am_issue(user, am_issue):
    issue_data = get_issue_data_from_am_issue(am_issue)
    try:
        issue = None
        issue = Issue.get_or_create_issue(
            user,
            journal=issue_data.get("journal"),
            volume=issue_data.get("volume"),
            number=issue_data.get("number"),
            season=issue_data.get("season"),
            year=issue_data.get("year"),
            month=issue_data.get("month"),
            supplement=issue_data.get("supplement"),
            markup_done=issue_data.get("markup_done"),
            issue_pid_suffix=issue_data.get("issue_pid_suffix"),
            order=issue_data.get("order"),
        )
        if issue:
            add_items(
                issue.add_sections,
                issue_data.get("sections_data"),
                issue,
                "Issue.add_sections",
            )
            add_items(
                issue.add_issue_titles,
                issue_data.get("titles"),
                issue,
                "Issue.add_issue_titles",
            )
            add_items(
                issue.add_bibliographic_strips,
                issue_data.get("bibliographic_strip_list"),
                issue,
                "Issue.add_bibliographic_strips",
            )
            add_items(issue.add_am_issue, am_issue, issue, "Issue.add_am_issue")
        return issue
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.sources.article_meta.create_issue_from_am_issue",
            detail={"am_issue": str(am_issue), "user": str(user)},
        )
        return issue


def add_items(add_function, items, issue, action_name):
    try:
        add_function(items)
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action=action_name,
            detail={"issue": str(issue), "items": items},
        )
