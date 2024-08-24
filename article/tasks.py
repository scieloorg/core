import logging
import sys
from datetime import datetime

from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from packtools.sps.formats import pubmed, pmc, crossref

from article.models import Article, ArticleFormat
from article.sources import xmlsps
from article.sources.preprint import harvest_preprints
from config import celery_app
from doi_manager.models import CrossRefConfiguration
from journal.models import Journal
from pid_provider.models import PidProviderXML
from pid_provider.provider import PidProvider
from tracker.models import UnexpectedEvent

from . import controller

User = get_user_model()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


@celery_app.task()
def load_funding_data(user, file_path):
    user = User.objects.get(pk=user)

    controller.read_file(user, file_path)


@celery_app.task(bind=True, name=_("load_article"))
def load_article(self, user_id=None, username=None, file_path=None, v3=None):
    user = _get_user(self.request, username, user_id)
    xmlsps.load_article(user, file_path=file_path, v3=v3)


def _items_to_load_article(from_date, force_update):
    if from_date:
        try:
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
        except Exception:
            from_date = None
    if not from_date:
        # obtém a última atualização de Article
        try:
            article = (
                Article.objects.filter(~Q(valid=True)).order_by("-updated").first()
            )
            if not article:
                article = (
                    Article.objects.filter(valid=True).order_by("-updated").first()
                )
                if article:
                    from_date = article.updated
        except Article.DoesNotExist:
            from_date = datetime(1900, 1, 1)

    if not from_date:
        from_date = datetime(1900, 1, 1)

    items = PidProviderXML.public_items(from_date)
    if force_update:
        yield from items

    for item in items:
        try:
            article = Article.objects.get(
                ~Q(valid=True),
                pid_v3=item.v3,
                updated__lt=item.updated,
                created__lt=item.created,
            )
            if article:
                yield item
        except Article.DoesNotExist:
            yield item


@celery_app.task(bind=True, name=_("load_articles"))
def load_articles(
    self, user_id=None, username=None, from_date=None, force_update=False
):
    try:
        user = _get_user(self.request, username, user_id)

        for item in _items_to_load_article(from_date, force_update):
            try:
                load_article.apply_async(
                    kwargs={
                        "file_path": item.current_version.file.path,
                        "user_id": user.id,
                        "username": user.username,
                        "v3": item.v3,
                    }
                )
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
    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.load_articles",
            },
        )


@celery_app.task(bind=True, name=_("load_preprints"))
def load_preprint(self, user_id, oai_pmh_preprint_uri):
    user = User.objects.get(pk=user_id)
    ## fazer filtro para não coletar tudo sempre
    harvest_preprints(oai_pmh_preprint_uri, user)


def get_function_format_xml(format_name):
    dict_functions_formats = {
        "pmc": pmc.pipeline_pmc,
        "pubmed": pubmed.pipeline_pubmed,
        "crossref": crossref.pipeline_crossref,
    }
    return dict_functions_formats.get(format_name)


def handler_formatting_error(article_format, message):
    article_format.save_format_xml(
        filename=None, format_xml=None, status="E", report={"exception_msg": message}
    )


def get_article_format(user, pid_v3, format_name):
    try:
        article = Article.objects.get(pid_v3=pid_v3)
    except Article.DoesNotExist:
        logging.info(f"Unable to convert article {pid_v3} to the specified format")
        return

    try:
        article_format = ArticleFormat.objects.get(article=article, format_name="pmc")
    except ArticleFormat.DoesNotExist:
        article_format = ArticleFormat.create_or_update(
            user=user, article=article, format_name=format_name, version=1
        )
    return article_format


@celery_app.task(bind=True)
def task_convert_xml_to_other_formats_for_articles(
    self, format_name, user_id=None, username=None, force_update=False
):
    journals = Journal.objects.filter(indexed_at__acronym=format_name)
    articles = Article.objects.filter(journal__in=journals)

    if not force_update:
        articles = articles.filter(article_format__isnull=True)

    try:
        task_function_dict = {
            "pubmed": convert_xml_to_pubmed_or_pmc_formats,
            "pmc": convert_xml_to_pubmed_or_pmc_formats,
            "crossref": convert_xml_to_crossref_format,
        }
        task_function = task_function_dict[format_name]
    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "article.tasks.task_convert_xml_to_other_formats_for_articles",
                "item": str(article),
            },
        )
        return

    for article in articles:
        try:
            task_function.apply_async(
                user_id=user_id,
                username=username,
                format_name=format_name,
            )
        except Exception as exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=exception,
                exc_traceback=exc_traceback,
                detail={
                    "task": "article.tasks.task_convert_xml_to_other_formats_for_articles",
                    "item": str(article),
                },
            )


@celery_app.task(bind=True)
def convert_xml_to_pubmed_or_pmc_formats(
    self, pid_v3, format_name, user_id=None, username=None
):
    user = _get_user(request=self.request, username=username, user_id=user_id)

    article_format = get_article_format(
        pid_v3=pid_v3, format_name=format_name, user=user
    )

    function_format = get_function_format_xml(format_name=format_name)

    content = function_format(article_format.article.xmltree)
    article_format.save_format_xml(
        format_xml=content,
        filename=article_format.article.sps_pkg_name + ".xml",
        status="S",
    )


@celery_app.task(bind=True)
def convert_xml_to_crossref_format(
    self, pid_v3, format_name, user_id=None, username=None
):
    user = _get_user(request=self.request, username=username, user_id=user_id)

    article_format = get_article_format(
        pid_v3=pid_v3, format_name=format_name, user=user
    )

    doi = article_format.article.doi.first()
    if not doi:
        handler_formatting_error(
            article_format=article_format,
            message=f"Unable to format because the article {pid_v3} has no DOI associated with it",
        )
        return

    prefix = doi.value.split("/")[0]
    try:
        data = CrossRefConfiguration.get_data(prefix)
    except CrossRefConfiguration.DoesNotExist:
        handler_formatting_error(
            article_format=article_format,
            message=f"Unable to convert article {pid_v3} to crossref format. CrossrefConfiguration missing",
        )
        return

    function_format = get_function_format_xml(format_name=format_name)
    content = function_format(article_format.article.xmltree, data)
    article_format.save_format_xml(
        format_xml=content,
        filename=article_format.article.sps_pkg_name + ".xml",
        status="S",
    )


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
                .filter(pid_v3_count__gt=1)
            )
        else:
            duplicates = (
                Article.objects.values("pid_v3")
                .annotate(pid_v3_count=Count("pid_v3"))
                .filter(pid_v3_count__gt=1)
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
