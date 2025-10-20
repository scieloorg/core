import logging
import sys
import traceback
from datetime import datetime, timedelta

from celery import group, shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, F, Prefetch, Q, Subquery
from django.utils.translation import gettext_lazy as _

from article import controller
from article.models import Article, ArticleFormat, ArticleSource, AMArticle
from article.sources.preprint import harvest_preprints
from article.sources.xmlsps import load_article
from collection.models import Collection
from config import celery_app
from core.utils.extracts_normalized_email import extracts_normalized_email
from core.utils.utils import _get_user, fetch_data
from core.utils.harvesters import AMHarvester, OPACHarvester
from journal.models import SciELOJournal, Journal
from pid_provider.choices import PPXML_STATUS_DONE, PPXML_STATUS_TODO, PPXML_STATUS_INVALID
from pid_provider.models import PidProviderXML
from pid_provider.provider import PidProvider
from researcher.models import ResearcherIdentifier
from tracker.models import UnexpectedEvent

User = get_user_model()


@celery_app.task()
def load_funding_data(user, file_path):
    user = User.objects.get(pk=user)

    controller.read_file(user, file_path)


@celery_app.task(bind=True, name=_("load_preprints"))
def load_preprint(self, user_id, oai_pmh_preprint_uri):
    user = User.objects.get(pk=user_id)
    ## fazer filtro para não coletar tudo sempre
    harvest_preprints(oai_pmh_preprint_uri, user)


@celery_app.task(bind=True)
def task_convert_xml_to_other_formats_for_articles(
    self, user_id=None, username=None, from_date=None, force_update=False
):
    try:
        user = _get_user(self.request, username, user_id)

        for item in Article.objects.filter(sps_pkg_name__isnull=False).iterator():
            logging.info(item.pid_v3)
            try:
                convert_xml_to_other_formats.apply_async(
                    kwargs={
                        "user_id": user.id,
                        "username": user.username,
                        "item_id": item.id,
                        "force_update": force_update,
                    }
                )
            except Exception as exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=exception,
                    exc_traceback=exc_traceback,
                    detail={
                        "task": "article.tasks.task_convert_xml_to_other_formats_for_articles",
                        "item": str(item),
                    },
                )
    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_convert_xml_to_other_formats_for_articles",
            },
        )


@celery_app.task(bind=True)
def convert_xml_to_other_formats(
    self, user_id=None, username=None, item_id=None, force_update=None
):
    user = _get_user(self.request, username, user_id)

    try:
        article = Article.objects.get(pk=item_id)
    except Article.DoesNotExist:
        logging.info(f"Not found {item_id}")
        return

    done = False
    try:
        article_format = ArticleFormat.objects.get(article=article)
        done = True
    except ArticleFormat.MultipleObjectsReturned:
        done = True
    except ArticleFormat.DoesNotExist:
        done = False
    logging.info(f"Done {done}")

    if not done or force_update:
        ArticleFormat.generate_formats(user, article=article)


@celery_app.task(bind=True)
def task_select_articles_to_complete_data(
    self,
    username=None,
    user_id=None,
    collection_acron_list=None,
    journal_acron_list=None,
    data_status_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_updated_date=None,
    until_updated_date=None,
    articlemeta_export_enable=False,
):
    """
    Task para carregar artigos de uma lista selecionada de periódicos.
    Dispara subtasks para cada periódico encontrado.
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        
        # Construir filtros para os artigos
        article_filters = {}
        
        # Obter IDs dos periódicos baseado nos filtros
        journal_id_list = Journal.get_ids(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
        )
        
        if journal_id_list:
            article_filters["journal__in"] = journal_id_list
        
        # Aplicar filtro de status se fornecido
        if not data_status_list:
            data_status_list = [
                DATA_STATUS_PENDING,
                DATA_STATUS_UNDEF,
                DATA_STATUS_INVALID,
            ]
        article_filters["data_status__in"] = data_status_list
        
        # Adicionar filtros de data se fornecidos
        if from_pub_year:
            article_filters["pub_year__gte"] = from_pub_year
        if until_pub_year:
            article_filters["pub_year__lte"] = until_pub_year
        if from_updated_date:
            article_filters["updated__gte"] = from_updated_date
        if until_updated_date:
            article_filters["updated__lte"] = until_updated_date
        
        # Processar artigos
        articles_processed = 0
        articles_skipped = 0
        
        for article in Article.objects.filter(**article_filters).iterator():
            if not article.pp_xml_id:
                try:
                    pp_xml = PidProviderXML.objects.get(v3=article.pid_v3)
                    article.pp_xml = pp_xml
                    article.save(update_fields=['pp_xml'])
                except PidProviderXML.DoesNotExist:
                    articles_skipped += 1
                    continue
            
            task_load_article_from_pp_xml.delay(
                pp_xml_id=article.pp_xml_id,
                pid_v3=article.pid_v3,
                user_id=user_id or user.id,
                username=username or user.username,
                articlemeta_export_enable=articlemeta_export_enable,
            )
            articles_processed += 1
        
        return {
            "status": "success",
            "message": "Complete data to articles",
            "articles_processed": articles_processed,
            "articles_skipped": articles_skipped,
            "filters": {
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_updated_date": from_updated_date,
                "until_updated_date": until_updated_date,
                "data_status_list": data_status_list,
            },
        }
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_select_articles_to_complete_data",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "data_status_list": data_status_list,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_updated_date": from_updated_date,
                "until_updated_date": until_updated_date,
            },
        )
        raise


@celery_app.task(bind=True)
def transfer_license_statements_fk_to_article_license(
    self, user_id=None, username=None
):
    user = _get_user(self.request, username, user_id)
    articles_to_update = []
    for instance in Article.objects.filter(article_license__isnull=True):

        new_license = None
        if (
            instance.license_statements.exists()
            and instance.license_statements.first().url
        ):
            new_license = instance.license_statements.first().url
        elif instance.license and instance.license.license_type:
            new_license = instance.license.license_type

        if new_license:
            instance.article_license = new_license
            instance.updated_by = user
            articles_to_update.append(instance)

    if articles_to_update:
        Article.objects.bulk_update(
            articles_to_update, ["article_license", "updated_by"]
        )
        logging.info("The article_license of model Articles have been updated")


def get_researcher_identifier_unnormalized():
    return ResearcherIdentifier.objects.filter(source_name="EMAIL").exclude(
        identifier__regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )


@celery_app.task(bind=True)
def normalize_stored_email(
    self,
):
    updated_list = []
    re_identifiers = get_researcher_identifier_unnormalized()

    for re_identifier in re_identifiers:
        email = extracts_normalized_email(raw_email=re_identifier.identifier)
        if email:
            re_identifier.identifier = email
            updated_list.append(re_identifier)

    ResearcherIdentifier.objects.bulk_update(updated_list, ["identifier"])


@celery_app.task(bind=True, name="task_export_articles_to_articlemeta")
def task_export_articles_to_articlemeta(
    self,
    collection_acron_list=None,
    journal_acron_list=None,
    year_of_publication=None,
    from_pub_year=None,
    until_pub_year=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=True,
    user_id=None,
    username=None,
):
    user = _get_user(self.request, username=username, user_id=user_id)

    return controller.bulk_export_articles_to_articlemeta(
        collection_acron_list=collection_acron_list,
        journal_acron_list=journal_acron_list,
        from_pub_year=from_pub_year,
        until_pub_year=until_pub_year,
        from_date=from_date,
        until_date=until_date,
        days_to_go_back=days_to_go_back,
        force_update=force_update,
    )


@celery_app.task(bind=True, name="task_export_article_to_articlemeta")
def task_export_article_to_articlemeta(
    self,
    pid_v3=None,
    collection_acron_list=None,
    force_update=True,
    user_id=None,
    username=None,
):
    """
    Export a single article to ArticleMeta Database.

    Args:
        pid_v3: Article PID v3
        force_update: Force update existing records
        user_id: User ID
        username: Username

    Returns:
        bool: True if export was successful, False otherwise.
    """
    try:
        if not pid_v3:
            raise ValueError("task_export_article_to_articlemeta requires pid_v3")

        article = Article.objects.get(pid_v3=pid_v3)

        user = _get_user(self.request, username=username, user_id=user_id)

        return controller.export_article_to_articlemeta(
            user,
            article,
            collection_acron_list=collection_acron_list,
            force_update=force_update,
        )

    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_export_article_to_articlemeta",
                "pid_v3": pid_v3,
                "force_update": force_update,
            },
        )


@celery_app.task(bind=True, name="task_load_article_from_pp_xml")
def task_load_article_from_pp_xml(
    self,
    pp_xml_id=None,
    pid_v3=None,
    user_id=None,
    username=None,
    collection_acron_list=None,
    articlemeta_export_enable=None,
    force_update=None,
    timeout=None,
    is_activate=None,
    version=None,
):
    """
    Carrega um artigo específico a partir de um PidProviderXML.

    Processa o XML armazenado no PidProviderXML, cria/atualiza o Article
    e opcionalmente exporta para ArticleMeta.

    Args:
        self: Instância da tarefa Celery
        pp_xml_id (int): ID do PidProviderXML a processar (obrigatório)
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa
        articlemeta_export_enable (bool, optional): Exporta para ArticleMeta após carregar

    Returns:
        None

    Side Effects:
        - Cria/atualiza Article no banco
        - Atualiza status do PidProviderXML para DONE
        - Verifica disponibilidade do artigo
        - Exporta para ArticleMeta se solicitado
        - Registra UnexpectedEvent em caso de erro

    Notes:
        - O XML é lido diretamente do arquivo armazenado no PidProviderXML
        - A verificação de disponibilidade valida URLs e assets do artigo
    """
    try:
        user = _get_user(self.request, username, user_id)

        pp_xml = None
        # Busca o PidProviderXML com suas relações
        if pp_xml_id:
            pp_xml = PidProviderXML.objects.select_related("current_version").get(
                id=pp_xml_id
            )

        # Carrega o artigo do arquivo XML
        article = load_article(
            user,
            v3=pid_v3,
            pp_xml=pp_xml,
        )
        pp_xml.collections.set(article.collections)

        # Verifica disponibilidade (URLs, assets, etc)
        article.check_availability(user, collection_acron_list, timeout, is_activate)

        # Exporta para ArticleMeta se solicitado
        if articlemeta_export_enable:
            controller.export_article_to_articlemeta(
                user,
                article,
                collection_acron_list,
                force_update,
                version=version,
            )

    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_load_article_from_pp_xml",
                "pp_xml_id": pp_xml_id,
                "articlemeta_export_enable": articlemeta_export_enable,
                "force_update": force_update,
            },
        )


@celery_app.task(bind=True, name="task_select_articles_to_load_from_api")
def task_select_articles_to_load_from_api(
    self,
    username=None,
    user_id=None,
    collection_acron_list=None,
    from_date=None,
    until_date=None,
    limit=None,
    timeout=None,
    force_update=None,
    auto_solve_pid_conflict=None,
    opac_url=None,
):
    """
    Tarefa orquestradora para carregar artigos de múltiplas coleções via API.

    Dispara tarefas paralelas para cada coleção, otimizando o processamento
    em larga escala. Se nenhuma coleção for especificada, processa todas as
    coleções conhecidas do SciELO.

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        collection_acron_list (list, optional): Lista de acrônimos das coleções.
            Se None, usa lista padrão com todas as coleções SciELO.
            Ex: ["scl", "arg", "mex", "esp"]
        from_date (str, optional): Data inicial para coleta (formato ISO)
        until_date (str, optional): Data final para coleta (formato ISO)
        limit (int, optional): Limite de artigos por coleção
        timeout (int, optional): Timeout em segundos para requisições HTTP
        force_update (bool, optional): Força atualização mesmo se já existe
        auto_solve_pid_conflict (bool, optional): Resolve conflitos de PID automaticamente

    Returns:
        None

    Side Effects:
        - Garante que coleções estão carregadas no banco
        - Dispara uma tarefa para cada coleção em collection_acron_list
        - Registra UnexpectedEvent em caso de erro

    Examples:
        # Carregar artigos de coleções específicas
        task_select_articles_to_load_from_api.delay(
            collection_acron_list=["scl", "mex"],
            from_date="2024-01-01",
            until_date="2024-12-31"
        )

        # Carregar artigos de todas as coleções com limite
        task_select_articles_to_load_from_api.delay(
            limit=100,
            force_update=True
        )
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        # Define coleções padrão se não especificadas
        # Garante que as coleções estão carregadas no banco
        if Collection.objects.count() == 0:
            Collection.load(user)

        if not collection_acron_list:
            collection_acron_list = Collection.get_acronyms()
        # Dispara tarefa para cada coleção
        for collection_acron in collection_acron_list:
            task_select_articles_to_load_from_collection_endpoint.apply_async(
                kwargs={
                    "username": username,
                    "user_id": user_id,
                    "collection_acron": collection_acron,
                    "from_date": from_date,
                    "until_date": until_date,
                    "limit": limit,
                    "timeout": timeout,
                    "force_update": force_update,
                    "auto_solve_pid_conflict": auto_solve_pid_conflict,
                    "opac_url": opac_url,
                }
            )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_select_articles_to_load_from_api",
                "collection_acron_list": collection_acron_list,
                "from_date": from_date,
                "until_date": until_date,
                "limit": limit,
                "timeout": timeout,
            },
        )


@celery_app.task(
    bind=True, name="task_select_articles_to_load_from_collection_endpoint"
)
def task_select_articles_to_load_from_collection_endpoint(
    self,
    username=None,
    user_id=None,
    collection_acron=None,
    from_date=None,
    until_date=None,
    limit=None,
    timeout=None,
    force_update=None,
    auto_solve_pid_conflict=None,
    opac_url=None,
):
    """
    Coleta artigos de uma coleção específica via endpoint OPAC ou ArticleMeta.

    Utiliza harvesters especializados para cada tipo de endpoint:
    - OPACHarvester: Para coleção Brasil (scl)
    - AMHarvester: Para demais coleções via ArticleMeta

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        collection_acron (str): Acrônimo da coleção (obrigatório).
            Ex: "scl", "mex", "arg"
        from_date (str, optional): Data inicial para coleta (formato ISO)
        until_date (str, optional): Data final para coleta (formato ISO)
        limit (int, optional): Limite de documentos a coletar
        timeout (int, optional): Timeout em segundos para requisições
        force_update (bool, optional): Força atualização de artigos existentes
        auto_solve_pid_conflict (bool, optional): Resolve conflitos de PID

    Returns:
        None

    Raises:
        ValueError: Se collection_acron não for fornecido

    Side Effects:
        - Dispara task_load_article_from_xml_url para cada documento
        - Registra UnexpectedEvent em caso de erro

    Notes:
        - OPAC é usado apenas para Brasil (scl) por questões de performance
        - ArticleMeta é usado para todas as outras coleções
    """
    try:
        if not collection_acron:
            raise ValueError("Missing collection_acron")

        # Seleciona o harvester apropriado baseado na coleção
        if collection_acron == "scl":
            harvester = OPACHarvester(
                opac_url or "www.scielo.br",
                collection_acron,
                from_date=from_date,
                until_date=until_date,
                limit=limit,
                timeout=timeout,
            )
        else:
            harvester = AMHarvester(
                "article",
                collection_acron,
                from_date=from_date,
                until_date=until_date,
                limit=limit,
                timeout=timeout,
            )

        # Itera sobre documentos e dispara tarefas individuais
        for document in harvester.harvest_documents():
            source_date = document.get("processing_date") or document.get("origin_date")
            task_load_article_from_xml_url.delay(
                username,
                user_id,
                collection_acron,
                document["pid_v2"],
                document["url"],
                source_date,
                force_update,
                auto_solve_pid_conflict,
            )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_select_articles_to_load_from_collection_endpoint",
                "collection_acron": collection_acron,
                "from_date": from_date,
                "until_date": until_date,
                "limit": limit,
                "timeout": timeout,
                "force_update": force_update,
            },
        )


@celery_app.task(bind=True, name="task_load_article_from_xml_url")
def task_load_article_from_xml_url(
    self,
    username=None,
    user_id=None,
    collection_acron=None,
    pid=None,
    xml_url=None,
    source_date=None,
    force_update=None,
    auto_solve_pid_conflict=None,
):
    """
    Carrega um artigo individual a partir de uma URL de XML.

    Cria ou atualiza um ArticleSource e processa o XML para criar/atualizar
    o artigo no banco de dados.

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        xml_url (str): URL do XML do artigo
            Ex: "https://www.scielo.br/scielo.php?script=sci_arttext&pid=..."
        source_date (str, optional): Data de última atualização na fonte
        force_update (bool, optional): Força reprocessamento mesmo se já completado
        auto_solve_pid_conflict (bool, optional): Resolve conflitos de PID automaticamente

    Returns:
        None

    Side Effects:
        - Cria/atualiza registro ArticleSource
        - Processa XML e cria/atualiza Article
        - Registra UnexpectedEvent em caso de erro

    Notes:
        - Pula processamento se ArticleSource já está COMPLETED e force_update=False
        - XML é baixado e armazenado localmente antes do processamento
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        # Cria ou atualiza ArticleSource
        am_article = AMArticle.create_or_update(
            pid, Collection.get(collection_acron), None, user
        )

        article_source = ArticleSource.create_or_update(
            user=user,
            url=xml_url,
            source_date=source_date,
            force_update=force_update,
            am_article=am_article,
        )
        article_source.complete_data(
            user=user,
            force_update=force_update,
            auto_solve_pid_conflict=auto_solve_pid_conflict,
        )

        if article_source.status != ArticleSource.StatusChoices.COMPLETED:
            return

        # Processa o XML
        task_load_article_from_pp_xml.delay(
            pp_xml_id=article_source.pid_provider_xml.id,
            user_id=user_id or user.id,
            username=username or user.username,
            force_update=force_update,
        )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_load_article_from_xml_url",
                "xml_url": xml_url,
                "source_date": source_date,
                "force_update": force_update,
            },
        )


@celery_app.task(bind=True, name="task_select_articles_to_load_from_article_source")
def task_select_articles_to_load_from_article_source(
    self,
    username=None,
    user_id=None,
    from_date=None,
    until_date=None,
    force_update=None,
    auto_solve_pid_conflict=None,
):
    """
    Processa ArticleSources pendentes ou que necessitam reprocessamento.

    Busca ArticleSources com status pendente ou erro e processa seus XMLs.
    Útil para reprocessar falhas anteriores ou completar processamentos interrompidos.

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        from_date (str, optional): Data inicial para filtrar ArticleSources
        until_date (str, optional): Data final para filtrar ArticleSources
        force_update (bool, optional): Força reprocessamento de todos
        auto_solve_pid_conflict (bool, optional): Resolve conflitos de PID

    Returns:
        None

    Side Effects:
        - Processa XMLs de ArticleSources selecionados
        - Atualiza status dos ArticleSources
        - Registra UnexpectedEvent em caso de erro

    Examples:
        # Reprocessar falhas dos últimos 7 dias
        task_select_articles_to_load_from_article_source.delay(
            from_date=(datetime.now() - timedelta(days=7)).isoformat(),
            force_update=True
        )
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        # Obtém queryset de ArticleSources para processar
        for article_source in ArticleSource.get_queryset_to_complete_data(
            from_date,
            until_date,
            force_update,
        ):
            article_source.complete_data(
                user=user,
                force_update=force_update,
                auto_solve_pid_conflict=auto_solve_pid_conflict,
            )
            if article_source.status != ArticleSource.StatusChoices.COMPLETED:
                return

            # Processa o XML
            task_load_article_from_pp_xml.delay(
                pp_xml_id=article_source.pid_provider_xml.id,
                user_id=user_id or user.id,
                username=username or user.username,
                force_update=force_update,
            )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_select_articles_to_load_from_article_source",
                "from_date": from_date,
                "until_date": until_date,
                "force_update": force_update,
            },
        )


@celery_app.task(bind=True)
def task_fix_article_status(
    self,
    username=None,
    user_id=None,
    collection_acron_list=None,
    journal_acron_list=None,
    mark_as_invalid=False,
    mark_as_public=False,
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
        task_fix_article_records_status.delay(
            collection_acron_list=["scl", "mex"],
            journal_acron_list=["abc", "xyz"],
            mark_as_invalid=True
        )

        # Marcar artigos como public e deduplicated
        task_fix_article_records_status.delay(
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
            "public": mark_as_public,
            "duplicated": mark_as_duplicated,
            "deduplicated": deduplicate,
        }

        if not any(operations.values()):
            raise ValueError("At least one marking operation must be specified")

        # Construir filtros para os periódicos
        journal_id_list = Journal.get_ids(collection_acron_list, journal_acron_list)

        # Iterar pelos periódicos e disparar subtarefas
        journals_processed = 0
        for journal_id in journal_id_list:
            qs = Article.objects.filter(journal__id=journal_id)
            if qs.count() == 0:
                continue
            task_fix_journal_articles_status.apply_async(
                kwargs={
                    "username": username,
                    "user_id": user_id,
                    "journal_id": journal_id,
                    "mark_as_invalid": mark_as_invalid,
                    "mark_as_public": mark_as_public,
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
                "journals": journal_acron_list,
            },
        }

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_fix_article_records_status",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "operations": {
                    "mark_as_invalid": mark_as_invalid,
                    "mark_as_public": mark_as_public,
                    "mark_as_duplicated": mark_as_duplicated,
                    "deduplicate": deduplicate,
                },
            },
        )
        raise


@celery_app.task(bind=True)
def task_fix_journal_articles_status(
    self,
    username=None,
    user_id=None,
    journal_id=None,
    collection_acron=None,
    journal_acron=None,
    mark_as_invalid=False,
    mark_as_public=False,
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

        # Buscar o periódico por ID ou acrônimo
        if journal_acron and collection_acron:
            journal_ids = Journal.get_ids(
                [collection_acron],
                [journal_acron],
            )
        elif journal_id:
            journal_ids = [journal_id]
        else:
            raise ValueError("Insufficient data to identify the journal")

        if Article.objects.filter(journal__id__in=journal_ids).count() == 0:
            return {
                "status": "no_articles",
                "journal_id": journal_id,
                "journal_acron": journal_acron,
                "collection_acron": collection_acron,
            }
        journal_id = journal_ids[0]
        if mark_as_invalid:
            Article.mark_items_as_invalid(journal_id=journal_id)

        if mark_as_public:
            Article.mark_items_as_public(journal_id=journal_id)

        if mark_as_duplicated:
            Article.mark_items_as_duplicated(journal_id=journal_id)

        if deduplicate:
            Article.deduplicate_items(user, journal_id=journal_id)

        return {
            "status": "success",
            "journal_id": journal_id,
            "journal_acron": journal_acron,
            "collection_acron": collection_acron,
            "operations_performed": {
                "mark_as_invalid": mark_as_invalid,
                "mark_as_public": mark_as_public,
                "mark_as_duplicated": mark_as_duplicated,
                "deduplicate": deduplicate,
            },
        }

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_fix_journal_articles_status",
                "journal_id": journal_id,
                "journal_acron": journal_acron,
                "collection_acron": collection_acron,
                "operations": {
                    "mark_as_invalid": mark_as_invalid,
                    "mark_as_public": mark_as_public,
                    "mark_as_duplicated": mark_as_duplicated,
                    "deduplicate": deduplicate,
                },
            },
        )
        raise


@celery_app.task(bind=True)
def task_load_articles(
    self,
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
):
    """
    Task para carregar artigos de uma lista selecionada de periódicos.
    Dispara subtasks para cada periódico encontrado.
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        proc_status_list = proc_status_list or [
            PPXML_STATUS_TODO,
            PPXML_STATUS_INVALID,
        ]
        # Construir filtros para os periódicos
        items = Journal.get_journal_issns(collection_acron_list, journal_acron_list)
        if items:
            # Iterar pelos periódicos e disparar subtarefas
            journals_processed = 0
            for journal_issns in items:
                # Filtrar ISSNs válidos
                issn_list = [issn for issn in journal_issns if issn]

                if not issn_list:  # Só dispara task se houver ISSNs
                    continue

                task_load_journal_articles.delay(
                    username=username,
                    user_id=user_id,
                    issn_list=issn_list,
                    articlemeta_export_enable=articlemeta_export_enable,
                    from_pub_year=from_pub_year,
                    until_pub_year=until_pub_year,
                    from_updated_date=from_updated_date,
                    until_updated_date=until_updated_date,
                    proc_status_list=proc_status_list,
                )
                journals_processed += 1

            return {
                "status": "success",
                "journals_processed": journals_processed,
                "filters": {
                    "collections": collection_acron_list,
                    "journals": journal_acron_list,
                    "from_pub_year": from_pub_year,
                    "until_pub_year": until_pub_year,
                    "from_updated_date": from_updated_date,
                    "until_updated_date": until_updated_date,
                    "proc_status_list": proc_status_list,
                },
            }

        else:
            # Se não há filtros, processa todos os artigos
            task_load_journal_articles.delay(
                username=username,
                user_id=user_id,
                issn_list=None,
                articlemeta_export_enable=articlemeta_export_enable,
                from_pub_year=from_pub_year,
                until_pub_year=until_pub_year,
                from_updated_date=from_updated_date,
                until_updated_date=until_updated_date,
                proc_status_list=proc_status_list,
            )
            return {
                "status": "success",
                "message": "Processing all articles without journal filters",
                "filters": {
                    "from_pub_year": from_pub_year,
                    "until_pub_year": until_pub_year,
                    "from_updated_date": from_updated_date,
                    "until_updated_date": until_updated_date,
                    "proc_status_list": proc_status_list,
                },
            }

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_load_articles",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "articlemeta_export_enable": articlemeta_export_enable,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_updated_date": from_updated_date,
                "until_updated_date": until_updated_date,
                "proc_status_list": proc_status_list,
            },
        )
        raise


@celery_app.task(bind=True)
def task_load_journal_articles(
    self,
    username=None,
    user_id=None,
    issn_list=None,
    articlemeta_export_enable=False,
    from_pub_year=None,
    until_pub_year=None,
    from_updated_date=None,
    until_updated_date=None,
    proc_status_list=None,
):
    """
    Task para carregar artigos de um periódico específico.
    Dispara subtasks para cada artigo encontrado.
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        proc_status_list = proc_status_list or [
            PPXML_STATUS_TODO,
            PPXML_STATUS_INVALID,
        ]
        # Buscar os XMLs usando os ISSNs do periódico
        items = PidProviderXML.get_queryset(
            issn_list=issn_list,
            from_pub_year=from_pub_year,
            until_pub_year=until_pub_year,
            from_updated_date=from_updated_date,
            until_updated_date=until_updated_date,
            proc_status_list=proc_status_list,
        )
        if not items.exists():
            return {
                "status": "success",
                "articles_found": 0,
                "message": "No articles found with the specified filters",
                "filters": {
                    "issn_list": issn_list,
                    "from_pub_year": from_pub_year,
                    "until_pub_year": until_pub_year,
                    "from_updated_date": from_updated_date,
                    "until_updated_date": until_updated_date,
                    "proc_status_list": proc_status_list,
                },
            }
        # Contador de artigos processados
        articles_processed = 0
        # Iterar sobre os itens e disparar tasks para cada artigo
        for item in items.iterator():
            task_load_article_from_pp_xml.delay(
                pp_xml_id=item.id,
                user_id=user_id or user.id,
                username=username or user.username,
                articlemeta_export_enable=articlemeta_export_enable,
            )
            articles_processed += 1
        return {
            "status": "success",
            "articles_processed": articles_processed,
            "operations": {
                "articlemeta_export_enable": articlemeta_export_enable,
            },
            "filters": {
                "issn_list": issn_list,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_updated_date": from_updated_date,
                "until_updated_date": until_updated_date,
                "proc_status_list": proc_status_list,
            },
        }

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_load_journal_articles",
                "issn_list": issn_list,
                "articlemeta_export_enable": articlemeta_export_enable,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_updated_date": from_updated_date,
                "until_updated_date": until_updated_date,
                "proc_status_list": proc_status_list,
            },
        )
        raise
