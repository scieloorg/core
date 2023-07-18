from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from article.sources import xmlsps
from article.sources.preprint import harvest_preprints
from xmlsps.models import XMLSPS
from article.models import Article
from config import celery_app
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
def load_article(self, user_id, file_path=None, xml=None):
    user = _get_user(self.request, user_id=user_id)
    xmlsps.load_article(user, file_path=file_path, xml=xml)


@celery_app.task(bind=True, name=_("load_articles"))
def load_articles(self, user_id=None):

    user_id = user_id or self.request.user.id
    from_date = Article.last_created_date()

    for item in XMLSPS.list(from_date):
        load_article.apply_async(args=(user_id, ), kwargs={"xml": item.xml})


@celery_app.task(bind=True, name=_("load_preprints"))
def load_preprint(self, user_id, oai_pmh_preprint_uri):
    user = _get_user(self.request, user_id=user_id)
    ## fazer filtro para não coletar tudo sempre
    harvest_preprints(oai_pmh_preprint_uri, user)
