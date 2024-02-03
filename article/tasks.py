import sys
from datetime import datetime

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from article.models import Article
from article.sources import xmlsps
from article.sources.preprint import harvest_preprints
from config import celery_app
from pid_provider.models import PidProviderXML
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
def load_article(self, user_id=None, username=None, file_path=None, xml=None, v3=None):
    user = _get_user(self.request, username, user_id)
    xmlsps.load_article(user, file_path=file_path, xml=xml, v3=v3)


def _items_to_load_article(from_date, force_update):
    if from_date:
        try:
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
        except Exception:
            from_date = None
    if not from_date:
        from_date = datetime(1900, 1, 1)

    items = PidProviderXML.public_items(from_date)
    if force_update:
        return items

    for item in items:
        try:
            article = Article.objects.get(pid_v3=item.v3)
            article_date = article.updated or article.created
            if article_date < (item.updated or item.created):
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
                        "xml": item.current_version.xml,
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
