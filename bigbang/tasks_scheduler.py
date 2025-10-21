"""
Funções de agendamento para tarefas do módulo article.tasks
Cada função cria um agendamento para sua respectiva tarefa Celery
"""

from django.utils.translation import gettext_lazy as _

from bigbang.utils.scheduler import delete_tasks, schedule_task

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

TASK_PRIORITY = 1


# ==============================================================================
# LIMPEZA DE TAREFAS ANTIGAS
# ==============================================================================

def delete_outdated_tasks(task_list=None):
    """
    Deleta todas as tarefas relacionadas aos módulos Article e PidProvider
    """
    task_list = task_list or [
        # Tarefas de Article com namespace completo
        "article.tasks.load_article_from_pp_xml",
        "article.tasks.load_articles",
        "article.tasks.task_mark_articles_as_deleted_without_pp_xml",
        "article.tasks.task_remove_duplicate_articles",
        "article.tasks.task_convert_xml_to_other_formats_for_articles",
        "article.tasks.convert_xml_to_other_formats",
        "article.tasks.task_load_article_from_xml_endpoint",
        
        # Tarefas de Article sem namespace (legacy)
        "article_complete_data",
        "convert_xml_to_other_formats",
        "load_articles",
        "load_funding_data",
        "load_preprints",
        "normalize_stored_email",
        "remove_duplicate_articles_task",
        "task_articles_complete_data",
        "task_convert_xml_to_other_formats_for_articles",
        "task_export_article_to_articlemeta",
        "task_export_articles_to_articlemeta",
        "task_load_article_from_article_source",
        "task_mark_articles_as_deleted_without_pp_xml",
        "transfer_license_statements_fk_to_article_license",
    ]
    delete_tasks(task_list)


# ==============================================================================
# AGENDAMENTO PRINCIPAL
# ==============================================================================

def schedule_tasks(username):
    """
    Executa todas as funções de agendamento de tarefas
    """
    enabled = False

    # Tarefas de Article mantidas
    schedule_task_select_articles_to_complete_data(username, enabled)
    schedule_task_export_articles_to_articlemeta(username, enabled)
    schedule_task_select_articles_to_load_from_api(username, enabled)
    schedule_task_select_articles_to_load_from_article_source(username, enabled)
    schedule_task_fix_article_status(username, enabled)
    schedule_task_load_articles(username, enabled)
    
    # Tarefas de issue
    schedule_export_issue_to_articlemeta(username, enabled)
    schedule_export_issues_to_articlemeta(username, enabled)
    schedule_load_issue_from_article_meta(username, enabled)
    
    # Tarefas de journal
    schedule_export_journal_to_articlemeta(username, enabled)
    schedule_export_journals_to_articlemeta(username, enabled)
    schedule_load_license_of_use_in_journal(username, enabled)
    schedule_fetch_and_process_journal_logos_in_collection(username, enabled)
    schedule_load_journal_from_article_meta(username, enabled)
    schedule_collect_journals_from_am(username, enabled)
    
    # Tarefas de pid_provider
    schedule_fix_pid_provider_xmls_status(username, enabled)

    # Tarefas de bigbang
    schedule_bigbang_start(username, enabled)
    schedule_bigbang_delete_outdated_tasks(username, enabled)


# ==============================================================================
# TAREFAS DE ARTICLE MANTIDAS
# ==============================================================================

def schedule_task_select_articles_to_complete_data(username, enabled=False):
    """
    Agenda a tarefa de completar dados de artigos incompletos
    """
    schedule_task(
        task="article.tasks.task_select_articles_to_complete_data",
        name="article.tasks.task_select_articles_to_complete_data",
        kwargs=dict(
            user_id=None,
            username=username,
            collection_acron_list=[],
            journal_acron_list=[],
            from_pub_year=None,
            until_pub_year=None,
            force_update=False,
            from_updated_date=None,
            until_updated_date=None,
            data_status_list=[],
            valid=None,
            pp_xml__isnull=True,
            sps_pkg_name__isnull=True,
            article_license__isnull=True,
        ),
        description=_("Complete missing data for articles"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="6",
        minute="1",
    )


def schedule_task_export_articles_to_articlemeta(username, enabled=False):
    """
    Agenda a tarefa de exportar artigos em lote para ArticleMeta
    """
    schedule_task(
        task="article.tasks.task_select_articles_to_export_to_articlemeta",
        name="article.tasks.task_select_articles_to_export_to_articlemeta",
        kwargs=dict(
            collection_acron_list=[],
            issn=None,
            number=None,
            volume=None,
            year_of_publication=None,
            from_date="2024-01-01",
            until_date="2024-12-31",
            days_to_go_back=None,
            force_update=True,
            user_id=None,
            username=username,
        ),
        description=_("Export articles in batch to ArticleMeta"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="23",
        minute="1",
    )


def schedule_task_select_articles_to_load_from_api(username, enabled=False):
    """
    Agenda a tarefa de carregar artigos de múltiplas coleções via API
    """
    schedule_task(
        task="article.tasks.task_select_articles_to_load_from_api",
        name="article.tasks.task_select_articles_to_load_from_api",
        kwargs=dict(
            username=username,
            user_id=None,
            collection_acron_list=["scl"],
            from_date="2024-01-01",
            until_date="2024-02-31",
            limit=100,
            timeout=10,
            force_update=False,
            auto_solve_pid_conflict=False,
            opac_url=None,
        ),
        description=_("Load articles from multiple collections via API"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="3",
        minute="1",
    )


def schedule_task_select_articles_to_load_from_article_source(username, enabled=False):
    """
    Agenda a tarefa de processar ArticleSources pendentes
    """
    schedule_task(
        task="article.tasks.task_select_articles_to_load_from_article_source",
        name="task_select_articles_to_load_from_article_source",
        kwargs=dict(
            username=username,
            user_id=None,
            from_date="2024-01-01",
            until_date="2024-12-31",
            force_update=False,
            auto_solve_pid_conflict=False,
        ),
        description=_("Process pending ArticleSources"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="*/6",
        minute="30",
    )


def schedule_task_fix_article_status(username, enabled=False):
    """
    Agenda a tarefa de corrigir status dos registros de artigos.
    
    Permite marcar artigos como inválidos, públicos ou duplicados,
    além de deduplicar registros conforme necessário.
    """
    schedule_task(
        task="article.tasks.task_fix_article_status",
        name="article.tasks.task_fix_article_status",
        kwargs=dict(
            username=username,
            user_id=None,
            collection_acron_list=None,
            journal_acron_list=None,
            mark_as_invalid=False,
            mark_as_public=False,
            mark_as_duplicated=False,
            deduplicate=False,
        ),
        description=_("Fix Article records status"),
        priority=5,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="*",
        minute="30",
    )


def schedule_task_load_articles(username, enabled=False):
    """
    Agenda a tarefa de carregar artigos do PidProviderXML
    """
    schedule_task(
        task="article.tasks.task_load_articles",
        name="article.tasks.task_load_articles",
        kwargs=dict(
            username=None,
            user_id=None,
            collection_acron_list=None,
            journal_acron_list=None,
            articlemeta_export_enable=None,
            from_pub_year=None,
            until_pub_year=None,
            from_updated_date=None,
            until_updated_date=None,
            proc_status_list=None,
        ),
        description=_("Load articles from PidProviderXML"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="2",
        minute="1",
    )


# ==============================================================================
# TAREFAS DE BIGBANG
# ==============================================================================

def schedule_bigbang_start(username, enabled=False):
    """
    Agenda a tarefa de start do bigbang
    """
    schedule_task(
        task="bigbang.tasks.task_start",
        name="bigbang.tasks.task_start",
        kwargs={},
        description=_("Start"),
        priority=1,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="12",
        minute="1",
    )


def schedule_bigbang_delete_outdated_tasks(username, enabled=False):
    """
    Agenda a tarefa de limpeza de tarefas obsoletas do Article
    
    Remove tarefas antigas e não utilizadas do módulo Article,
    mantendo o scheduler limpo e organizado.
    """
    schedule_task(
        task="bigbang.tasks.task_delete_outdated_tasks",
        name="bigbang.tasks.task_delete_outdated_tasks",
        kwargs=dict(
            username=username,
            user_id=None,
            task_list=[],  # Lista vazia indica exclusão de todas as tarefas obsoletas
        ),
        description=_("Delete outdated tasks"),
        priority=10,  # Baixa prioridade
        enabled=enabled,
        run_once=False,
        day_of_week="0",  # Executa apenas aos domingos
        hour="3",  # Durante a madrugada
        minute="0",
    )


# ==============================================================================
# TAREFAS DE JOURNAL
# ==============================================================================

def schedule_load_journal_from_article_meta(username, enabled=False):
    """
    Agenda a tarefa de carga de dados de journals obtidos do AM e Core
    """
    schedule_task(
        task="journal.tasks.load_journal_from_article_meta",
        name="Carga de dados de journals obtidos do AM e Core",
        kwargs=dict(
            load_data=False,
            collection_acron="scl",
        ),
        description=_("Carga de dados de journals obtidos do AM e Core"),
        priority=1,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="12",
        minute="1",
    )


def schedule_collect_journals_from_am(username, enabled=False):
    """
    Agenda a tarefa de coleta de journals da fonte AM
    """
    schedule_task(
        task="journal.tasks.load_journal_from_article_meta",
        name="Coleta de journals da fonte AM",
        kwargs=dict(
            load_data=True,
            collection_acron="scl",
        ),
        description=_("Coleta de journals da fonte AM"),
        priority=1,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="12",
        minute="1",
    )


def schedule_fetch_and_process_journal_logos_in_collection(username, enabled=False):
    """
    Agenda a tarefa de buscar e processar logos de journals por coleção
    """
    schedule_task(
        task="journal.tasks.fetch_and_process_journal_logos_in_collection",
        name="fetch_and_process_journal_logos_in_collection",
        kwargs=dict(
            collection_acron3=None,
            user_id=None,
            username=username,
        ),
        description=_("Fetch and process journal logos for all collections"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="6",
        hour="3",
        minute="1",
    )


def schedule_load_license_of_use_in_journal(username, enabled=False):
    """
    Agenda a tarefa de carregar licenças de uso em journals
    """
    schedule_task(
        task="journal.tasks.load_license_of_use_in_journal",
        name="load_license_of_use_in_journal",
        kwargs=dict(
            issn_scielo=None,
            collection_acron3=None,
            user_id=None,
            username=username,
        ),
        description=_("Load licenses of use in journals"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="0",
        hour="5",
        minute="1",
    )


def schedule_export_journals_to_articlemeta(username, enabled=False):
    """
    Agenda a tarefa de exportar journals em lote para ArticleMeta
    """
    schedule_task(
        task="journal.tasks.task_export_journals_to_articlemeta",
        name="task_export_journals_to_articlemeta",
        kwargs=dict(
            collection_acron_list=[],
            journal_acron_list=None,
            from_date=None,
            until_date=None,
            days_to_go_back=None,
            force_update=True,
            user_id=None,
            username=username,
        ),
        description=_("Export journals in batch to ArticleMeta"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="21",
        minute="1",
    )


def schedule_export_journal_to_articlemeta(username, enabled=False):
    """
    Agenda a tarefa de exportar um journal individual para ArticleMeta
    """
    schedule_task(
        task="journal.tasks.task_export_journal_to_articlemeta",
        name="task_export_journal_to_articlemeta",
        kwargs=dict(
            issn=None,
            force_update=True,
            user_id=None,
            username=username,
        ),
        description=_("Export individual journal to ArticleMeta"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="2",
        minute="1",
    )


# ==============================================================================
# TAREFAS DE ISSUE
# ==============================================================================

def schedule_load_issue_from_article_meta(username, enabled=False):
    """
    Agenda a tarefa de carregar issues do ArticleMeta
    """
    schedule_task(
        task="issue.tasks.task_load_issue_from_article_meta",
        name="task_load_issue_from_article_meta",
        kwargs=dict(
            user_id=None,
            username=username,
            collection="scl",
            issn_scielo="0034-8910",
            from_date=None,
            until_date=None,
            limit=None,
            force_update=False,
            timeout=None,
            reset=None,
        ),
        description=_("Load issues from ArticleMeta"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="8",
        minute="1",
    )


def schedule_export_issues_to_articlemeta(username, enabled=False):
    """
    Agenda a tarefa de exportar issues em lote para ArticleMeta
    """
    schedule_task(
        task="issue.tasks.task_export_issues_to_articlemeta",
        name="task_export_issues_to_articlemeta",
        kwargs=dict(
            collection_acron_list=[],
            journal_acron_list=[],
            publication_year=None,
            volume=None,
            number=None,
            supplement=None,
            force_update=True,
            user_id=None,
            username=username,
        ),
        description=_("Export issues in batch to ArticleMeta"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="20",
        minute="1",
    )


def schedule_export_issue_to_articlemeta(username, enabled=False):
    """
    Agenda a tarefa de exportar um issue individual para ArticleMeta
    """
    schedule_task(
        task="issue.tasks.task_export_issue_to_articlemeta",
        name="task_export_issue_to_articlemeta",
        kwargs=dict(
            user_id=None,
            username=None,
            collection_acron=None,
            journal_acron=None,
            publication_year=None,
            volume=None,
            number=None,
            supplement=None,
            force_update=None,
        ),
        description=_("Export individual issue to ArticleMeta"),
        priority=TASK_PRIORITY,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="2",
        minute="1",
    )


# ==============================================================================
# TAREFAS DE PID PROVIDER
# ==============================================================================

def schedule_fix_pid_provider_xmls_status(username, enabled=False):
    """
    Agenda a tarefa de corrigir status dos XMLs do PID Provider.
    
    Permite marcar XMLs como inválidos, públicos ou duplicados,
    além de deduplicar registros conforme necessário.
    """
    schedule_task(
        task="pid_provider.tasks.task_fix_pid_provider_xmls_status",
        name="pid_provider.tasks.task_fix_pid_provider_xmls_status",
        kwargs=dict(
            username=username,
            user_id=None,
            collection_acron_list=None,
            journal_acron_list=None,
            mark_as_invalid=True,
            # mark_as_public=False,
            mark_as_duplicated=False,
            deduplicate=False,
        ),
        description=_("Fix PID Provider XMLs status"),
        priority=5,
        enabled=enabled,
        run_once=False,
        day_of_week="*",
        hour="*",
        minute="1",
    )