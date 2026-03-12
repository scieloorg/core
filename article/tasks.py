import logging
import sys

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from article import controller
from article.models import Article, ArticleFormat, ArticleSource, AMArticle
from article.sources.preprint import harvest_preprints
from article.sources.xmlsps import load_article
from collection.models import Collection
from config import celery_app
from core.models import License
from core.utils.extracts_normalized_email import extracts_normalized_email
from core.utils.utils import _get_user
from journal.models import Journal
from pid_provider.models import PidProviderXML
from researcher.models import ResearcherIdentifier
from tracker.models import UnexpectedEvent

User = get_user_model()


@celery_app.task()
def load_funding_data(user, file_path):
    """
    Carrega dados de financiamento a partir de um arquivo CSV ou similar.

    Processa um arquivo de dados de financiamento e carrega as informações
    no banco de dados, associando-as aos artigos correspondentes.

    Args:
        user (int): ID do usuário que está executando a tarefa
        file_path (str): Caminho absoluto para o arquivo contendo dados de financiamento

    Returns:
        None

    Side Effects:
        - Lê arquivo de financiamento do sistema de arquivos
        - Cria/atualiza registros de financiamento no banco
        - Registra logs de processamento e erros

    Notes:
        - Utiliza controller.read_file para processamento
        - O formato do arquivo deve seguir o padrão esperado pelo sistema
    """
    user = User.objects.get(pk=user)

    controller.read_file(user, file_path)


@celery_app.task(bind=True, name=_('load_preprints'))
def load_preprint(self, user_id, oai_pmh_preprint_uri):
    """
    Coleta e carrega preprints de um endpoint OAI-PMH específico.

    Conecta-se a um servidor OAI-PMH para coletar metadados de preprints
    e carregá-los no sistema para posterior processamento.

    Args:
        self: Instância da tarefa Celery
        user_id (int): ID do usuário executando a tarefa (obrigatório)
        oai_pmh_preprint_uri (str): URI do endpoint OAI-PMH para coleta (obrigatório)

    Returns:
        None

    Side Effects:
        - Conecta ao endpoint OAI-PMH especificado
        - Coleta metadados de preprints disponíveis
        - Cria/atualiza registros de preprints no banco
        - Registra logs de processamento e eventuais erros

    Todo:
        - Implementar filtro para não coletar todos os registros sempre
        - Adicionar suporte a coleta incremental por data

    Examples:
        # Coletar preprints de repositório específico
        load_preprint.delay(
            user_id=1,
            oai_pmh_preprint_uri="http://repo.example.com/oai/request"
        )

    Notes:
        - Utiliza harvest_preprints para o processamento efetivo
        - A coleta completa pode ser demorada em repositórios grandes
    """
    user = User.objects.get(pk=user_id)
    ## fazer filtro para não coletar tudo sempre
    harvest_preprints(oai_pmh_preprint_uri, user)


@celery_app.task(bind=True)
def task_convert_xml_to_other_formats_for_articles(
    self, user_id=None, username=None, from_date=None, force_update=False
):
    """
    Dispara conversão de XML para outros formatos para todos os artigos com SPS package.

    Itera por todos os artigos que possuem sps_pkg_name e dispara
    tarefas individuais de conversão para cada um.

    Args:
        self: Instância da tarefa Celery
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa
        from_date (str, optional): Data inicial para filtrar artigos (não implementado)
        force_update (bool, optional): Força reprocessamento mesmo se já convertido

    Returns:
        None

    Side Effects:
        - Dispara múltiplas subtarefas convert_xml_to_other_formats
        - Registra UnexpectedEvent em caso de erro
        - Processa todos os artigos com sps_pkg_name

    Examples:
        # Converter todos os artigos
        task_convert_xml_to_other_formats_for_articles.delay(
            user_id=1,
            force_update=True
        )
    """
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
    """
    Converte XML de um artigo específico para outros formatos (HTML, PDF, etc.).

    Verifica se o artigo já possui formatos gerados e, caso necessário,
    gera os formatos a partir do XML SPS armazenado.

    Args:
        self: Instância da tarefa Celery
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa
        item_id (int): ID do artigo a ser processado (obrigatório)
        force_update (bool, optional): Força regeneração mesmo se já existe

    Returns:
        None

    Side Effects:
        - Cria/atualiza registros ArticleFormat
        - Gera arquivos HTML, PDF e outros formatos
        - Registra logs de processamento

    Notes:
        - Pula processamento se ArticleFormat já existe e force_update=False
        - Utiliza ArticleFormat.generate_formats para conversão
    """
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
def transfer_license_statements_fk_to_article_license(
    self, user_id=None, username=None
):
    """
    Migra informações de licença de license_statements para o campo license.

    Processa artigos que não possuem license mas têm license_statements,
    transferindo as informações para o campo direto license.

    Args:
        self: Instância da tarefa Celery
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa

    Returns:
        None

    Side Effects:
        - Atualiza campo license em artigos
        - Cria registros License se necessário
        - Executa bulk_update para otimizar performance
        - Registra logs de processamento

    Notes:
        - Processa apenas artigos com license=None
        - Usa o primeiro license_statement como referência
        - Cria License automaticamente se não existir
    """
    user = _get_user(self.request, username, user_id)
    articles_to_update = []
    for instance in Article.objects.filter(license__isnull=True):
        if not instance.license_statements.exists():
            continue

        first = instance.license_statements.first()
        instance.license = first.license
        if not instance.license and first.data:
            data = first.data
            instance.license = License.create_or_update(user, license_type=data.get("license_type"), version=data.get("license_version"))
            
        if not instance.license:
            continue
        instance.updated_by = user
        articles_to_update.append(instance)

    if articles_to_update:
        Article.objects.bulk_update(
            articles_to_update, ["license", "updated_by"]
        )
        logging.info("The license of model Articles have been updated")


def get_researcher_identifier_unnormalized():
    """
    Retorna identificadores de e-mail que não seguem formato padrão RFC 5322.

    Filtra objetos ResearcherIdentifier que possuem source_name="EMAIL" 
    mas cujo campo identifier não corresponde ao padrão de e-mail válido.

    Returns:
        QuerySet: Queryset de ResearcherIdentifier com e-mails mal formatados

    Notes:
        - Usa regex para identificar e-mails fora do padrão
        - Utilizada pela tarefa normalize_stored_email para identificar registros a corrigir
        - Regex verifica formato básico: usuario@dominio.extensao
    """
    return ResearcherIdentifier.objects.filter(source_name="EMAIL").exclude(
        identifier__regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    )


@celery_app.task(bind=True)
def normalize_stored_email(
    self,
):
    """
    Normaliza e corrige endereços de e-mail mal formatados no banco de dados.

    Busca identificadores de pesquisadores do tipo EMAIL que não seguem
    o padrão RFC 5322 e aplica normalização para corrigir formatos inválidos.

    Args:
        self: Instância da tarefa Celery

    Returns:
        None

    Side Effects:
        - Identifica e-mails com formato inválido usando regex
        - Aplica normalização através de extracts_normalized_email
        - Executa bulk_update para otimizar performance em lotes
        - Registra logs de processamento

    Examples:
        # Executar normalização de e-mails
        normalize_stored_email.delay()

    Notes:
        - Processa apenas ResearcherIdentifier com source_name="EMAIL"
        - Usa regex para identificar e-mails que não seguem formato padrão
        - Operação é idempotente - pode ser executada múltiplas vezes
        - Performance otimizada com bulk_update para grandes volumes

    See Also:
        - get_researcher_identifier_unnormalized(): Função auxiliar para filtros
        - extracts_normalized_email(): Função de normalização de e-mails
    """
    updated_list = []
    re_identifiers = get_researcher_identifier_unnormalized()

    for re_identifier in re_identifiers:
        email = extracts_normalized_email(raw_email=re_identifier.identifier)
        if email:
            re_identifier.identifier = email
            updated_list.append(re_identifier)

    ResearcherIdentifier.objects.bulk_update(updated_list, ["identifier"])


@celery_app.task(bind=True)
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
    force_update=None,
    user_id=None,
    username=None,
):
    """
    Exporta artigos em lote para a base de dados ArticleMeta com filtros flexíveis.

    Processa e exporta múltiplos artigos para o sistema ArticleMeta baseado
    em critérios de filtragem por coleção, periódico, ano ou data.

    Args:
        self: Instância da tarefa Celery
        collection_acron_list (list, optional): Lista de acrônimos de coleções
        journal_acron_list (list, optional): Lista de acrônimos de periódicos
        year_of_publication (int, optional): Ano específico de publicação
        from_pub_year (int, optional): Ano inicial para filtro de publicação
        until_pub_year (int, optional): Ano final para filtro de publicação
        from_date (str, optional): Data inicial para filtro (formato ISO)
        until_date (str, optional): Data final para filtro (formato ISO)
        days_to_go_back (int, optional): Número de dias para retroceder da data atual
        force_update (bool, optional): Força reprocessamento mesmo se já exportado
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa

    Returns:
        dict: Resultado da operação com estatísticas de processamento

    Side Effects:
        - Exporta múltiplos artigos para ArticleMeta
        - Atualiza status de exportação dos artigos
        - Registra logs de processamento
        - Registra UnexpectedEvent em caso de erro

    Examples:
        # Exportar por coleção e período
        task_export_articles_to_articlemeta.delay(
            collection_acron_list=["scl", "arg"],
            from_pub_year=2023,
            until_pub_year=2024
        )

        # Exportar artigos dos últimos 7 dias
        task_export_articles_to_articlemeta.delay(
            days_to_go_back=7,
            force_update=True
        )

    Notes:
        - Utiliza controller.bulk_export_articles_to_articlemeta internamente
        - Pode processar grandes volumes de dados
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        result = controller.bulk_export_articles_to_articlemeta(
            user,
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_pub_year=from_pub_year,
            until_pub_year=until_pub_year,
            from_date=from_date,
            until_date=until_date,
            days_to_go_back=days_to_go_back,
            force_update=force_update,
        )
        
        return result
        
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_export_articles_to_articlemeta",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "year_of_publication": year_of_publication,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_date": str(from_date) if from_date else None,
                "until_date": str(until_date) if until_date else None,
                "days_to_go_back": days_to_go_back,
                "force_update": force_update,
                "user_id": user_id,
                "username": username,
                "task_id": self.request.id if hasattr(self.request, 'id') else None,
            },
        )
        
        # Re-raise para que o Celery possa tratar a exceção adequadamente
        raise


@celery_app.task(bind=True)
def task_export_article_to_articlemeta(
    self,
    pid_v3=None,
    collection_acron_list=None,
    force_update=True,
    user_id=None,
    username=None,
):
    """
    Exporta um artigo específico para a base de dados ArticleMeta.

    Processa e exporta um único artigo identificado pelo PID v3
    para o sistema ArticleMeta, com controle de atualizações forçadas.

    Args:
        self: Instância da tarefa Celery
        pid_v3 (str, optional): PID v3 do artigo a exportar (obrigatório)
        collection_acron_list (list, optional): Lista de acrônimos de coleções para filtro
        force_update (bool): Força reexportação mesmo se já exportado
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa

    Returns:
        bool: True se exportação foi bem-sucedida, False caso contrário

    Side Effects:
        - Exporta artigo específico para ArticleMeta
        - Atualiza status de exportação do artigo
        - Registra logs de processamento
        - Registra UnexpectedEvent em caso de erro

    Raises:
        ValueError: Se pid_v3 não for fornecido
        Article.DoesNotExist: Se artigo com o PID não for encontrado

    Examples:
        # Exportar artigo específico
        task_export_article_to_articlemeta.delay(
            pid_v3="S1234-56782024000100001",
            force_update=True
        )

    Notes:
        - Utiliza controller.export_article_to_articlemeta internamente
        - Requer que o artigo exista na base local antes da exportação
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


@celery_app.task(bind=True)
def task_fix_article_status(
    self,
    username=None,
    user_id=None,
    collection_acron_list=None,
    journal_acron_list=None,
    journal_id=None,
    mark_as_invalid=False,
    mark_as_public=False,
    mark_as_duplicated=False,
    deduplicate=False,
):
    """
    Marca artigos com diferentes status baseado em filtros de coleções e periódicos.

    Aceita filtros por lista de coleções/periódicos ou um journal_id direto.
    Itera pelos periódicos correspondentes e aplica as operações de marcação.

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        collection_acron_list (list, optional): Lista de acrônimos de coleções
        journal_acron_list (list, optional): Lista de acrônimos de periódicos
        journal_id (int, optional): ID direto de um periódico específico
        mark_as_invalid (bool): Se True, marca artigos como invalid
        mark_as_public (bool): Se True, marca artigos como public
        mark_as_duplicated (bool): Se True, marca artigos como duplicated
        deduplicate (bool): Se True, marca artigos como deduplicated

    Returns:
        dict: Resumo da operação com contadores

    Side Effects:
        - Altera status de artigos no banco
        - Registra UnexpectedEvent em caso de erro

    Examples:
        task_fix_article_status.delay(
            collection_acron_list=["scl"],
            mark_as_invalid=True,
            mark_as_public=True,
        )

        task_fix_article_status.delay(
            journal_id=42,
            deduplicate=True,
        )
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        operations = {
            "invalid": mark_as_invalid,
            "public": mark_as_public,
            "duplicated": mark_as_duplicated,
            "deduplicated": deduplicate,
        }

        if not any(operations.values()):
            raise ValueError("At least one marking operation must be specified")

        # Determinar lista de journal_ids a processar
        if journal_id:
            journal_id_list = [journal_id]
        else:
            journal_id_list = Journal.get_ids(collection_acron_list, journal_acron_list)

        journals_processed = 0

        for jid in journal_id_list:
            if Article.objects.filter(journal_id=jid).count() == 0:
                continue

            if mark_as_invalid:
                Article.mark_items_as_invalid(journal_id=jid)

            if mark_as_public:
                Article.mark_items_as_public(journal_id=jid)

            if mark_as_duplicated or deduplicate:
                Article.deduplicate_items(
                    user,
                    journal_id=jid,
                    mark_as_duplicated=mark_as_duplicated,
                    deduplicate=deduplicate,
                )

            journals_processed += 1

        return {
            "status": "success",
            "journals_processed": journals_processed,
            "operations": {k: v for k, v in operations.items() if v},
            "filters": {
                "collections": collection_acron_list,
                "journals": journal_acron_list,
                "journal_id": journal_id,
            },
        }

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_fix_article_status",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "journal_id": journal_id,
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
def task_check_article_availability(
    self,
    user_id=None,
    username=None,
    article_id=None,
    collection_acron_list=None,
    timeout=None,
    is_activate=None,
    force_update=False,
):
    """
    Verifica e atualiza o status de disponibilidade de um artigo específico.

    Executa verificações de URLs, assets e outros recursos do artigo
    para determinar se está completamente disponível online.

    Args:
        self: Instância da tarefa Celery
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa
        article_id (int, optional): ID do artigo a verificar (obrigatório)
        collection_acron_list (list, optional): Lista de acrônimos de coleções para filtro
        timeout (int, optional): Timeout em segundos para verificações HTTP
        is_activate (bool, optional): Se deve ativar artigo após verificação
        force_update (bool): Força nova verificação mesmo se recente

    Returns:
        None

    Side Effects:
        - Atualiza status de disponibilidade do artigo
        - Verifica URLs de assets (PDF, HTML, etc.)
        - Registra timestamps de última verificação
        - Registra UnexpectedEvent em caso de erro

    Notes:
        - Utiliza Article.check_availability para executar verificações
        - Pode ser utilizada para monitoramento de saúde dos artigos
    """
    try:
        user = _get_user(self.request, username, user_id)
        article = Article.objects.get(id=article_id)
        article.check_availability(user)
    except Exception as exception:
        logging.exception(f"Error processing article ID {article_id}: {str(exception)}")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_check_article_availability",
                "article_id": article_id,
                "collection_acron_list": collection_acron_list,
                "timeout": timeout,
                "is_activate": is_activate,
                "force_update": force_update,
            },
        )


@celery_app.task(bind=True)
def task_dispatch_articles(
    self,
    username=None,
    user_id=None,
    # --- filtros comuns ---
    collection_acron_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_date=None,
    until_date=None,
    force_update=None,
    export_to_articlemeta=False,
    auto_solve_pid_conflict=None,
    # --- ativa pid_provider ---
    proc_status_list=None,
    # --- ativa article ---
    data_status_list=None,
    # --- ativa harvest (qualquer um) ---
    limit=None,
    timeout=None,
    opac_url=None,
    # --- ativa article_source ---
    article_source_status_list=None,
):
    """
    Tarefa orquestradora que dispara processamento em lote de artigos.

    Utiliza ArticleIteratorBuilder para selecionar artigos baseado em
    múltiplos critérios e dispara task_process_article_pipeline para
    cada item encontrado, permitindo processamento paralelo.

    Args:
        self: Instância da tarefa Celery
        username (str, optional): Nome do usuário executando a tarefa
        user_id (int, optional): ID do usuário executando a tarefa
        collection_acron_list (list, optional): Filtro por acrônimos de coleções
        journal_acron_list (list, optional): Filtro por acrônimos de periódicos
        from_pub_year (int, optional): Ano inicial de publicação
        until_pub_year (int, optional): Ano final de publicação
        from_date (str, optional): Data inicial (formato ISO)
        until_date (str, optional): Data final (formato ISO)
        force_update (bool, optional): Força reprocessamento
        export_to_articlemeta (bool): Exporta para ArticleMeta após processamento
        auto_solve_pid_conflict (bool, optional): Resolve conflitos de PID automaticamente
        proc_status_list (list, optional): Status do pid_provider para filtro
        data_status_list (list, optional): Status do article para filtro
        limit (int, optional): Limite máximo de artigos a processar
        timeout (int, optional): Timeout para operações HTTP
        opac_url (str, optional): URL base do OPAC para harvest
        article_source_status_list (list, optional): Status do article_source para filtro

    Returns:
        dict: Resumo com contadores de dispatched/skipped

    Examples:
        # Processamento padrão por coleção
        task_dispatch_articles.delay(collection_acron_list=["scl"])

        # Múltiplas fontes simultaneamente
        task_dispatch_articles.delay(
            proc_status_list=["todo"],
            data_status_list=["invalid"],
            article_source_status_list=["error"],
            limit=500
        )

    Notes:
        - Ver ArticleIteratorBuilder para detalhes sobre iteradores ativados
        - Cada artigo encontrado gera uma subtarefa independente
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        common_kwargs = {
            "user_id": user.id,
            "username": user.username,
            "force_update": force_update,
            "export_to_articlemeta": export_to_articlemeta,
            "auto_solve_pid_conflict": auto_solve_pid_conflict,
        }

        dispatched = skipped = 0

        for item_kwargs in controller.ArticleIteratorBuilder(
            user=user,
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_pub_year=from_pub_year,
            until_pub_year=until_pub_year,
            from_date=from_date,
            until_date=until_date,
            proc_status_list=proc_status_list,
            data_status_list=data_status_list,
            article_source_status_list=article_source_status_list,
            limit=limit,
            timeout=timeout,
            opac_url=opac_url,
            force_update=force_update,
        ):
            if item_kwargs is None:
                skipped += 1
                continue
            logging.info(f"Dispatching article with kwargs: {item_kwargs}")
            task_process_article_pipeline.delay(**item_kwargs, **common_kwargs)
            dispatched += 1

        return {
            "status": "success",
            "dispatched": dispatched,
            "skipped": skipped,
        }

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_dispatch_articles",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_date": from_date,
                "until_date": until_date,
                "proc_status_list": proc_status_list,
                "data_status_list": data_status_list,
                "article_source_status_list": article_source_status_list,
                "force_update": force_update,
                "export_to_articlemeta": export_to_articlemeta,
            },
        )
        raise

@celery_app.task(bind=True)
def task_process_article_pipeline(
    self,
    # Entrada para fluxo A (XML URL → ArticleSource → PidProviderXML)
    xml_url=None,
    collection_acron=None,
    pid=None,
    source_date=None,
    # Entrada para fluxo B (ArticleSource existente → PidProviderXML)
    article_source_id=None,
    # Entrada direta para etapa C (PidProviderXML → Article)
    pp_xml_id=None,
    # Controle do fluxo
    export_to_articlemeta=False,
    collection_acron_list=None,
    force_update=None,
    auto_solve_pid_conflict=None,
    version=None,
    user_id=None,
    username=None,
):
    """
    Pipeline principal de processamento de artigos com múltiplos pontos de entrada.

    Implementa um pipeline flexível que pode iniciar em diferentes estágios:
    - Fluxo A: XML URL → ArticleSource → PidProviderXML → Article
    - Fluxo B: ArticleSource existente → PidProviderXML → Article  
    - Fluxo C: PidProviderXML → Article (entrada direta)

    Args:
        self: Instância da tarefa Celery
        xml_url (str, optional): URL do XML para fluxo A (requer collection_acron e pid)
        collection_acron (str, optional): Acrônimo da coleção (obrigatório com xml_url)
        pid (str, optional): PID do artigo (obrigatório com xml_url)
        source_date (datetime, optional): Data da fonte para fluxo A
        article_source_id (int, optional): ID do ArticleSource para fluxo B
        pp_xml_id (int, optional): ID do PidProviderXML para fluxo C
        export_to_articlemeta (bool): Se True, exporta para ArticleMeta após processamento
        collection_acron_list (list, optional): Lista de coleções para exportação
        force_update (bool, optional): Força reprocessamento mesmo se existir
        auto_solve_pid_conflict (bool, optional): Resolve conflitos de PID automaticamente
        version (str, optional): Versão específica a processar
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa

    Returns:
        None

    Side Effects:
        - Cria/atualiza ArticleSource (fluxo A)
        - Cria/atualiza PidProviderXML
        - Cria/atualiza Article
        - Verifica disponibilidade do artigo
        - Exporta para ArticleMeta se solicitado
        - Registra UnexpectedEvent em caso de erro

    Raises:
        ValueError: Se nenhum ponto de entrada válido for fornecido
                   Se xml_url fornecido sem collection_acron ou pid

    Examples:
        # Fluxo completo a partir de URL
        task_process_article_pipeline.delay(
            xml_url="http://example.com/article.xml",
            collection_acron="scl", 
            pid="S1234-56782024000100001",
            export_to_articlemeta=True
        )

        # A partir de ArticleSource existente
        task_process_article_pipeline.delay(
            article_source_id=123,
            force_update=True
        )

        # Entrada direta via PidProviderXML
        task_process_article_pipeline.delay(
            pp_xml_id=456,
            export_to_articlemeta=True
        )
    """
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        
        if xml_url:
            if not collection_acron:
                raise ValueError("collection_acron is required when xml_url is provided")
            if not pid:
                raise ValueError("pid is required when xml_url is provided")
            am_article = AMArticle.create_or_update(
                pid, Collection.get(collection_acron), None, user
            )
            if not am_article:
                raise ValueError(
                    f"Failed to create or update AMArticle with pid: {pid} and collection: {collection_acron}"
                )

            article_source = ArticleSource.create_or_update(
                user=user,
                url=xml_url,
                source_date=source_date,
                force_update=force_update,
                am_article=am_article,
                auto_solve_pid_conflict=auto_solve_pid_conflict,
            )
            pp_xml_id = article_source.pid_provider_xml.id
        
        if article_source_id:
            article_source = ArticleSource.objects.get(id=article_source_id)
            article_source.add_pid_provider(
                user=user,
                force_update=force_update,
                auto_solve_pid_conflict=auto_solve_pid_conflict,
            )
            pp_xml_id = article_source.pid_provider_xml.id

        if not pp_xml_id:
            raise ValueError(
                "No valid entry point provided. Please provide either xml_url, "
                "article_source_id, pp_xml_id or pid_v3."
            )

        pp_xml = PidProviderXML.objects.select_related(
            "current_version"
        ).get(id=pp_xml_id)

        article = load_article(user, pp_xml=pp_xml)
        pp_xml.collections.set(article.collections)

        article.check_availability(user, force_update=export_to_articlemeta or force_update)
        
        if export_to_articlemeta:
            task_export_article_to_articlemeta.delay(
                pid_v3=article.pid_v3,
                collection_acron_list=collection_acron_list,
                force_update=force_update,
                user_id=user.id,
                username=user.username,
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_process_article_pipeline",
                "xml_url": xml_url,
                "article_source_id": article_source_id,
                "pp_xml_id": pp_xml_id,
                "pid": pid,
                "collection_acron": collection_acron,
                "export_to_articlemeta": export_to_articlemeta,
                "force_update": force_update,
            },
        )
