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
from article.models import Article, ArticleFormat, ArticleSource
from article.sources.preprint import harvest_preprints
from article.sources.xmlsps import load_article
from collection.models import Collection
from config import celery_app
from core.utils.extracts_normalized_email import extracts_normalized_email
from core.utils.utils import _get_user, fetch_data
from journal.models import SciELOJournal
from pid_provider.choices import PPXML_STATUS_DONE, PPXML_STATUS_TODO
from pid_provider.models import PidProviderXML
from pid_provider.provider import PidProvider
from researcher.models import ResearcherIdentifier
from tracker.models import UnexpectedEvent

User = get_user_model()


@celery_app.task()
def load_funding_data(user, file_path):
    user = User.objects.get(pk=user)

    controller.read_file(user, file_path)


def _items_to_load_article():
    return (
        PidProviderXML.objects.select_related("current_version")
        .filter(proc_status=PPXML_STATUS_TODO)
        .iterator()
    )


def items_to_load_article_with_valid_false():
    # Obtém os objetos PidProviderXMl onde o campo pid_v3 de article e v3 possuem o mesmo valor
    articles = Article.objects.filter(valid=False).values("pid_v3")
    return PidProviderXML.objects.filter(v3__in=Subquery(articles)).iterator()


@celery_app.task(bind=True, name="task_load_articles")
def task_load_articles(
    self,
    user_id=None,
    username=None,
):
    try:
        user = _get_user(self.request, username, user_id)

        generator_articles = (
            PidProviderXML.objects.select_related("current_version")
            .filter(proc_status=PPXML_STATUS_TODO)
            .iterator()
        )

        for item in generator_articles:
            try:
                article = load_article(
                    user,
                    file_path=item.current_version.file.path,
                    v3=item.v3,
                    pp_xml=item,
                )
                if article and article.valid:
                    item.proc_status = PPXML_STATUS_DONE
                    item.save()
            except Exception as exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=exception,
                    exc_traceback=exc_traceback,
                    detail={
                        "task": "article.tasks.load_articles",
                        "item": str(item),
                    },
                )

        task_mark_articles_as_deleted_without_pp_xml.apply_async(
            kwargs=dict(
                user_id=user_id or user.id,
                username=username or user.username,
            )
        )
    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.load_articles",
            },
        )


@celery_app.task(bind=True, name="task_mark_articles_as_deleted_without_pp_xml")
def task_mark_articles_as_deleted_without_pp_xml(self, user_id=None, username=None):
    """
    Tarefa Celery para marcar artigos como DATA_STATUS_DELETED quando pp_xml é None.

    Args:
        user_id: ID do usuário (opcional)
        username: Nome do usuário (opcional)
    """
    try:
        user = _get_user(self.request, username, user_id)

        updated_count = Article.mark_as_deleted_articles_without_pp_xml(user)

        logging.info(
            f"Task completed successfully. {updated_count} articles marked as deleted."
        )

    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_mark_articles_as_deleted_without_pp_xml",
            },
        )

        logging.error(
            f"Error in task_mark_articles_as_deleted_without_pp_xml: {exception}"
        )


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
def task_articles_complete_data(
    self, user_id=None, username=None, from_date=None, force_update=False
):
    try:
        user = _get_user(self.request, username, user_id)

        for item in Article.objects.iterator():
            try:
                article_complete_data.apply_async(
                    kwargs={
                        "user_id": user.id,
                        "username": user.username,
                        "item_id": item.id,
                    }
                )
            except Exception as exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=exception,
                    exc_traceback=exc_traceback,
                    detail={
                        "task": "article.tasks.task_articles_complete_data",
                        "item": str(item),
                    },
                )
    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_articles_complete_data",
            },
        )


@celery_app.task(bind=True)
def article_complete_data(
    self, user_id=None, username=None, item_id=None, force_update=None
):
    user = _get_user(self.request, username, user_id)
    try:
        item = Article.objects.get(pk=item_id)
        if item.pid_v3 and not item.sps_pkg_name:
            item.sps_pkg_name = PidProvider.get_sps_pkg_name(item.pid_v3)
            item.save()
    except Article.DoesNotExist:
        pass


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


def remove_duplicate_articles(pid_v3=None):
    ids_to_exclude = []
    try:
        if pid_v3:
            duplicates = (
                Article.objects.filter(pid_v3=pid_v3)
                .values("pid_v3")
                .annotate(pid_v3_count=Count("pid_v3"))
                .filter(pid_v3_count__gt=1, valid=False)
            )
        else:
            duplicates = (
                Article.objects.values("pid_v3")
                .annotate(pid_v3_count=Count("pid_v3"))
                .filter(pid_v3_count__gt=1, valid=False)
            )
        for duplicate in duplicates:
            article_ids = (
                Article.objects.filter(pid_v3=duplicate["pid_v3"])
                .order_by("created")[1:]
                .values_list("id", flat=True)
            )
            ids_to_exclude.extend(article_ids)

        if ids_to_exclude:
            Article.objects.filter(id__in=ids_to_exclude).delete()
    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.remove_duplicates_articles",
            },
        )


@celery_app.task(bind=True)
def remove_duplicate_articles_task(self, user_id=None, username=None, pid_v3=None):
    remove_duplicate_articles(pid_v3)


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


@celery_app.task(bind=True, name="task_get_opac_xmls")
def task_get_opac_xmls(
    self,
    username=None,
    user_id=None,
    begin_date=None,
    end_date=None,
    limit=None,
    pages=None,
    force_update=None,
    domain=None,
    collection_acron=None,
    timeout=None,
    auto_solve_pid_conflict=None,
):
    """
    API Response
    {
        "begin_date":"2023-06-01 00-00-00",
        "collection":"scl",
        "dictionary_date": "Sat, 01 Jul 2023 00:00:00 GMT",
        "documents":{
            "JFhVphtq6czR6PHMvC4w38N": {
                "aop_pid":"",
                "create":"Sat, 28 Nov 2020 23:42:43 GMT",
                "default_language":"en",
                "journal_acronym":"aabc",
                "pid":"S0001-37652012000100017",
                "pid_v1":"S0001-3765(12)08400117",
                "pid_v2":"S0001-37652012000100017",
                "pid_v3":"JFhVphtq6czR6PHMvC4w38N",
                "publication_date":"2012-05-22",
                "update":"Fri, 30 Jun 2023 20:57:30 GMT"
            },
            "ZZYxjr9xbVHWmckYgDwBfTc":{
                "aop_pid":"",
                "create":"Sat, 28 Nov 2020 23:42:37 GMT",
                "default_language":"en",
                "journal_acronym":"aabc",
                "pid":"S0001-37652012000100014",
                "pid_v1":"S0001-3765(12)08400114",
                "pid_v2":"S0001-37652012000100014",
                "pid_v3":"ZZYxjr9xbVHWmckYgDwBfTc",
                "publication_date":"2012-02-24",
                "update":"Fri, 30 Jun 2023 20:56:59 GMT",
            }
        }
    }
    """
    page = 1
    domain = domain or "www.scielo.br"
    limit = limit or 100
    collection_acron = collection_acron or "scl"
    end_date = end_date or datetime.utcnow().isoformat()[:10]
    timeout = timeout or 5
    begin_date = begin_date or "2000-01-01"

    user = _get_user(self.request, username=username, user_id=user_id)

    while True:
        try:
            uri = (
                f"https://{domain}/api/v1/counter_dict?end_date={end_date}"
                f"&begin_date={begin_date}&limit={limit}&page={page}"
            )
            response = fetch_data(uri, json=True, timeout=timeout, verify=True)

            pages = pages or response["pages"]
            documents = response["documents"]

        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "task_get_opac_xmls",
                    "uri": uri,
                },
            )

        else:
            for pid_v3, document in documents.items():
                try:
                    # Processa diretamente os dados do artigo e chama provide_pid_for_opac_and_am_xml
                    acron = document["journal_acronym"]
                    xml_uri = f"https://www.scielo.br/j/{acron}/a/{pid_v3}/?format=xml"
                    origin_date = datetime.strptime(
                        document.get("update") or document.get("create"),
                        "%a, %d %b %Y %H:%M:%S %Z",
                    ).isoformat()[:10]
                    year = document["publication_date"][:4]

                    article_source = ArticleSource.create_or_update(
                        user,
                        url=xml_uri,
                        source_date=origin_date,
                        force_update=force_update,
                    )
                    article_source.process_xml(
                        user, load_article, force_update, auto_solve_pid_conflict
                    )

                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "task": "task_get_opac_xmls",
                            "pid_v3": pid_v3,
                            "document": document,
                        },
                    )

        finally:
            page += 1
            if page > pages:
                break


@celery_app.task(bind=True, name="task_load_article_from_article_source")
def task_load_article_from_article_source(
    self,
    username=None,
    user_id=None,
    force_update=None,
    status__in=None,
    auto_solve_pid_conflict=None,
):
    try:
        user = _get_user(self.request, username=username, user_id=user_id)
        ArticleSource.process_xmls(
            user, load_article, status__in, force_update, auto_solve_pid_conflict
        )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "task_load_article_from_article_source",
                "status__in": status__in,
                "force_update": force_update,
            },
        )


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
            ValueError("task_export_article_to_articlemeta requires pid_v3")

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


@celery_app.task(bind=True, name="task_select_articles_to_load_from_pid_provider")
def task_select_articles_to_load_from_pid_provider(
    self,
    user_id=None,
    username=None,
    collection_acron_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_updated_date=None,
    until_updated_date=None,
    proc_status_list=None,
    articlemeta_export_enable=None,
    force_update=None,
    version=None,
):
    """
    Carrega artigos em lote a partir de registros PidProviderXML.

    PidProviderXML é o sistema central de gerenciamento de PIDs (identificadores
    persistentes) dos artigos. Esta tarefa processa XMLs armazenados no sistema
    de PIDs.

    Args:
        self: Instância da tarefa Celery
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa
        collection_acron_list (list, optional): Lista de acrônimos de coleções
        journal_acron_list (list, optional): Lista de acrônimos de periódicos
        from_pub_year (int, optional): Ano inicial de publicação
        until_pub_year (int, optional): Ano final de publicação
        from_updated_date (str, optional): Data inicial de atualização
        until_updated_date (str, optional): Data final de atualização
        proc_status_list (list, optional): Lista de status a processar
            Ex: [PPXML_STATUS_TODO, PPXML_STATUS_ERROR]
        articlemeta_export_enable (bool, optional): Exporta para ArticleMeta após carregar

    Returns:
        None

    Side Effects:
        - Dispara task_load_article_from_pp_xml para cada PidProviderXML
        - Exporta para ArticleMeta se articlemeta_export_enable=True
        - Registra UnexpectedEvent em caso de erro

    Examples:
        # Carregar artigos de 2024 de periódicos específicos
        task_select_articles_to_load_from_pid_provider.delay(
            journal_acron_list=["abc", "xyz"],
            from_pub_year=2024,
            until_pub_year=2024,
            articlemeta_export_enable=True
        )
    """
    try:
        user = _get_user(self.request, username, user_id)

        logging.info("add_collections_to_pid_provider_items")
        controller.get_pp_xml_ids()

        logging.info("get_pp_xml_ids")
        # Busca PidProviderXMLs baseado nos filtros
        logging.info(dict(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_pub_year=from_pub_year,
            until_pub_year=until_pub_year,
            from_updated_date=from_updated_date,
            until_updated_date=until_updated_date,
            proc_status_list=proc_status_list,
        ))
        pp_xml_items = controller.get_pp_xml_ids(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            from_pub_year=from_pub_year,
            until_pub_year=until_pub_year,
            from_updated_date=from_updated_date,
            until_updated_date=until_updated_date,
            proc_status_list=proc_status_list,
        )
        # Cria grupo de tarefas para processamento paralelo
        for pp_xml_id in pp_xml_items.iterator():
            task_load_article_from_pp_xml.delay(
                pp_xml_id=pp_xml_id,
                user_id=user_id or user.id,
                username=username or user.username,
                collection_acron_list=collection_acron_list,
                articlemeta_export_enable=articlemeta_export_enable,
                force_update=force_update,
                version=version,
            )

    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_select_articles_to_load_from_pid_provider",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "from_pub_year": from_pub_year,
                "until_pub_year": until_pub_year,
                "from_updated_date": from_updated_date,
                "until_updated_date": until_updated_date,
                "proc_status_list": proc_status_list,
                "articlemeta_export_enable": articlemeta_export_enable,
            },
        )


@celery_app.task(bind=True, name="task_load_article_from_pp_xml")
def task_load_article_from_pp_xml(
    self,
    pp_xml_id,
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

        # Busca o PidProviderXML com suas relações
        pp_xml = PidProviderXML.objects.select_related("current_version").get(
            id=pp_xml_id
        )

        # Carrega o artigo do arquivo XML
        article = load_article(
            user,
            file_path=pp_xml.current_version.file.path,
            v3=pp_xml.v3,
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


@celery_app.task(bind=True, name="task_complete_pid_provider_data")
def task_complete_pid_provider_data(
    self,
    user_id=None,
    username=None,
):
    """
    Carrega artigos em lote a partir de registros PidProviderXML.

    PidProviderXML é o sistema central de gerenciamento de PIDs (identificadores
    persistentes) dos artigos. Esta tarefa processa XMLs armazenados no sistema
    de PIDs.

    Args:
        self: Instância da tarefa Celery
        user_id (int, optional): ID do usuário executando a tarefa
        username (str, optional): Nome do usuário executando a tarefa
        collection_acron_list (list, optional): Lista de acrônimos de coleções
        journal_acron_list (list, optional): Lista de acrônimos de periódicos
        from_pub_year (int, optional): Ano inicial de publicação
        until_pub_year (int, optional): Ano final de publicação
        from_updated_date (str, optional): Data inicial de atualização
        until_updated_date (str, optional): Data final de atualização
        proc_status_list (list, optional): Lista de status a processar
            Ex: [PPXML_STATUS_TODO, PPXML_STATUS_ERROR]
        articlemeta_export_enable (bool, optional): Exporta para ArticleMeta após carregar

    Returns:
        None

    Side Effects:
        - Dispara task_load_article_from_pp_xml para cada PidProviderXML
        - Exporta para ArticleMeta se articlemeta_export_enable=True
        - Registra UnexpectedEvent em caso de erro

    Examples:
        # Carregar artigos de 2024 de periódicos específicos
        task_complete_pid_provider_data.delay(
            journal_acron_list=["abc", "xyz"],
            from_pub_year=2024,
            until_pub_year=2024,
            articlemeta_export_enable=True
        )
    """
    try:
        user = _get_user(self.request, username, user_id)

        controller.add_collections_to_pid_provider_items()

    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_complete_pid_provider_data",
            },
        )
