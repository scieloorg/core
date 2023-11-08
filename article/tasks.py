from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from article.models import Article
from article.sources import xmlsps
from article.sources.preprint import harvest_preprints
from config import celery_app
from pid_provider.models import PidProviderXML

from . import controller

User = get_user_model()

@celery_app.task()
def load_funding_data(user, file_path):
    user = User.objects.get(pk=user)
    
    controller.read_file(user, file_path)


@celery_app.task(bind=True, name=_("load_article"))
def load_article(self, user_id, file_path=None, xml=None):
    user = User.objects.get(pk=user_id)
    xmlsps.load_article(user, file_path=file_path, xml=xml)


@celery_app.task(bind=True, name=_("load_articles"))
def load_articles(self, user_id=None):
    from_date = Article.last_created_date()

    for item in PidProviderXML.public_items(from_date):
        load_article.apply_async(args=(user_id,), kwargs={"xml": item.current_version.xml})


@celery_app.task(bind=True, name=_("load_preprints"))
def load_preprint(self, user_id, oai_pmh_preprint_uri):
    user = User.objects.get(pk=user_id)
    ## fazer filtro para não coletar tudo sempre
    harvest_preprints(oai_pmh_preprint_uri, user)
