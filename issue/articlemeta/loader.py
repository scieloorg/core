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
            action="issue.articlemeta.loader.harvest_issue_identifiers",
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
            action="issue.articlemeta.loader.harvest_issue_data",
            detail={"url": url},
        )
        item = {}
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
        
        # Corrigido: não redefine harvested_data se já existe
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
            action="issue.articlemeta.loader.load_am_issue",
            detail={
                "collection": collection.acron3 if collection else None,
                "url": url,
                "pid": pid,
                "force_update": force_update,
            },
        )
        return None


def complete_am_issue(user, am_issue):
    try:
        detail = {}

        detail["am_issue"] = str(am_issue)
        if not am_issue:
            raise ValueError("am_issue is required")

        detail["am_issue_url"] = str(am_issue.url)
        if not am_issue.url:
            raise ValueError("am_issue.url is required")
        
        harvested_data = harvest_issue_data(am_issue.url)
        detail["harvested_data"] = str(harvested_data)
        am_issue.status = harvested_data.get("status")
        am_issue.data = harvested_data.get("data")
        am_issue.updated_by = user
        am_issue.save()
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.loader.complete_am_issue",
            detail=detail,
        )


def get_issue_data_from_am_issue(am_issue, user=None):
    """
    Extrai e ajusta dados do AMIssue para criação de Issue.

    Args:
        am_issue: Instância de AMIssue
        user: Usuário para completar dados se necessário

    Returns:
        Dict com dados ajustados para Issue ou None se falhar
    """
    try:
        # Extrair dados do issue
        detail = {
            "am_issue": str(am_issue),
        }

        if not am_issue:
            raise ValueError("am_issue is required")
        
        am_data = am_issue.data
        if not am_data:
            if user:
                complete_am_issue(user, am_issue)
                am_data = am_issue.data
        
        if not am_data:
            raise ValueError(f"get_issue_data_from_am_issue: Unable to get am_issue.data from {am_issue}")
        detail["am_data"] = str(am_data)

        issue_data = am_data["issue"]
        if not issue_data:
            raise ValueError(f"get_issue_data_from_am_issue: Unable to get issue data from {am_data}")
        detail["raw_issue_data"] = str(issue_data)

        issue_dict = rename_issue_dictionary_keys([issue_data], correspondencia_issue)
        detail["renamed_issue_data"] = str(issue_dict)

        # Retornar dados ajustados para Issue
        extracted_data = extract_data_from_harvested_data(issue_dict, am_issue.pid)

        scielo_journal = SciELOJournal.objects.get(
            collection=am_issue.collection,
            issn_scielo=am_issue.pid[:9],
        )
        extracted_data["journal"] = scielo_journal.journal
        return extracted_data
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.loader.get_issue_data_from_am_issue",
            detail=detail,
        )
        return None


def create_issue_from_am_issue(user, am_issue):
    """
    Cria Issue a partir de AMIssue.
    
    Args:
        user: Usuário responsável
        am_issue: Instância do AMIssue
        
    Returns:
        Issue criado ou None se falhar
    """
    issue = None
    
    try:
        issue_data = get_issue_data_from_am_issue(am_issue, user)
        if not issue_data:
            raise ValueError(f"Unable to extract issue data from {am_issue}")
                  
        issue = Issue.get_or_create(
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
            issue.add_am_issue(user, am_issue)
            load_issue_sections(user, issue, am_issue, issue_data)
            load_issue_titles(user, issue, am_issue, issue_data)
            load_bibliographic_strips(user, issue, am_issue, issue_data)
                
        return issue
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.loader.create_issue_from_am_issue",
            detail={"am_issue": str(am_issue), "user": str(user)},
        )
        return issue


def _extract_field(field_name, field_value, issue_data, am_issue, user):
    """
    Extrai um campo específico dos dados do issue.
    
    Prioridade: field_value > issue_data > am_issue
    
    Args:
        field_name: Nome do campo em issue_data
        field_value: Valor direto do campo (opcional)
        issue_data: Dados extraídos do AMIssue (opcional)
        am_issue: Instância de AMIssue (opcional)
        user: Usuário para extração
        
    Returns:
        Valor do campo ou None
        
    Raises:
        ValueError: Se nenhuma fonte de dados disponível
    """
    if field_value:
        return field_value
    
    if issue_data:
        try:
            return issue_data[field_name]
        except KeyError as e:
            # Campo não encontrado em issue_data
            pass
    
    if am_issue:
        data = get_issue_data_from_am_issue(am_issue, user)
        if not data:
            raise ValueError(f"Unable to extract issue data from {am_issue}")
        return data.get(field_name)
    
    raise ValueError(f"am_issue, issue_data or {field_name} is required")


def load_issue_sections(user, issue, am_issue=None, issue_data=None, sections_data=None, collection=None):
    """
    Carrega sections para um Issue existente.
    
    Args:
        user: Usuário responsável
        issue: Instância de Issue
        am_issue: Instância de AMIssue (opcional)
        issue_data: Dados extraídos do AMIssue (opcional)
        sections_data: Dados das sections (opcional, prioridade máxima)
        collection: Collection (obrigatório se am_issue não fornecido)
        
    Returns:
        bool: True se carregou com sucesso, False caso contrário
    """
    try:
        if not issue:
            raise ValueError("Issue is required")
        
        sections = _extract_field("sections_data", sections_data, issue_data, am_issue, user)
        if not sections:
            if '"v49"' in str(issue_data):
                raise ValueError("No sections found, but issue_data contains 'v49'")
            if '"v049"' in str(issue_data):
                raise ValueError("No sections found, but issue_data contains 'v049'")
            return True
        
        coll = collection or (am_issue.collection if am_issue else None)
        if not coll:
            raise ValueError("collection is required when am_issue is not provided")
            
        issue.add_sections(user, sections, coll)
        return True
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.loader.load_issue_sections",
            detail={
                "issue": str(issue),
                "am_issue": str(am_issue) if am_issue else None,
            },
        )
        return False


def load_issue_titles(user, issue, am_issue=None, issue_data=None, issue_titles=None):
    """
    Carrega títulos para um Issue existente.
    
    Args:
        user: Usuário responsável
        issue: Instância de Issue
        am_issue: Instância de AMIssue (opcional)
        issue_data: Dados extraídos do AMIssue (opcional)
        issue_titles: Lista de títulos (opcional, prioridade máxima)
        
    Returns:
        bool: True se carregou com sucesso, False caso contrário
    """
    try:
        if not issue:
            raise ValueError("Issue is required")
        
        titles = _extract_field("issue_titles", issue_titles, issue_data, am_issue, user)
        if not titles:
            logging.info("No issue titles found")
            return True
            
        issue.add_issue_titles(user, titles)
        return True
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.loader.load_issue_titles",
            detail={
                "issue": str(issue),
                "am_issue": str(am_issue) if am_issue else None,
            },
        )
        return False


def load_bibliographic_strips(user, issue, am_issue=None, issue_data=None, bibliographic_strips=None):
    """
    Carrega bibliographic strips para um Issue existente.
    
    Args:
        user: Usuário responsável
        issue: Instância de Issue
        am_issue: Instância de AMIssue (opcional)
        issue_data: Dados extraídos do AMIssue (opcional)
        bibliographic_strips: Lista de strips (opcional, prioridade máxima)
        
    Returns:
        bool: True se carregou com sucesso, False caso contrário
    """
    try:
        if not issue:
            raise ValueError("Issue is required")
        
        strips = _extract_field("bibliographic_strip_list", bibliographic_strips, issue_data, am_issue, user)
        if not strips:
            logging.info("No bibliographic strips found")
            return True
            
        issue.add_bibliographic_strips(user, strips)
        return True
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            action="issue.articlemeta.loader.load_bibliographic_strips",
            detail={
                "issue": str(issue),
                "am_issue": str(am_issue) if am_issue else None,
            },
        )
        return False
