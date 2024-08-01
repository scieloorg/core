import logging
import sys
from datetime import datetime

from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from packtools.sps.formats import pmc


from article.models import Article, ArticleFormat, Journal
from article.sources import xmlsps
from article.sources.preprint import harvest_preprints
from config import celery_app
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
            article = Article.objects.filter(
                ~Q(valid=True)
            ).order_by("-updated").first()
            if not article:
                article = Article.objects.filter(valid=True).order_by("-updated").first()
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
def transfer_license_statements_fk_to_article_license(self, user_id=None, username=None):
    user = _get_user(self.request, username, user_id)
    articles_to_update = []
    for instance in Article.objects.filter(article_license__isnull=True):

        new_license = None
        if instance.license_statements.exists() and instance.license_statements.first().url:
            new_license = instance.license_statements.first().url
        elif instance.license and instance.license.license_type:
            new_license = instance.license.license_type
        
        if new_license:
            instance.article_license = new_license
            instance.updated_by = user
            articles_to_update.append(instance)

    if articles_to_update:
        Article.objects.bulk_update(articles_to_update, ['article_license', 'updated_by'])
        logging.info("The article_license of model Articles have been updated")


def remove_duplicate_articles(pid_v3=None):
    ids_to_exclude = []
    try:
        if pid_v3:
            duplicates = Article.objects.filter(pid_v3=pid_v3).values("pid_v3").annotate(pid_v3_count=Count("pid_v3")).filter(pid_v3_count__gt=1)
        else:
            duplicates = Article.objects.values("pid_v3").annotate(pid_v3_count=Count("pid_v3")).filter(pid_v3_count__gt=1)
        for duplicate in duplicates:
            article_ids = Article.objects.filter(
                pid_v3=duplicate["pid_v3"]
            ).order_by("created")[1:].values_list("id", flat=True)
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

@celery_app.task(bind=True)
def create_files_articles_pubmed_pmc(self, user_id=None, username=None):
    pipeline = pmc.pipeline_pmc
    journals = Journal.objects.filter(Q(indexed_at__name="Pubmed") | Q(indexed_at__acronym="pmc"))
    articles = Article.objects.filter(journal__in=journals)
