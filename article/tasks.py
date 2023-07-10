from article import models
from config import celery_app
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.utils import DataError
from django.core.exceptions import ObjectDoesNotExist
from article.sources import preprint


from packtools.sps.models.article_ids import ArticleIds
from packtools.sps.utils import xml_utils
from .utils import article_utils

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


class ArticleSaveError(Exception):
    ...



@celery_app.task()
def load_funding_data(user, file_path):
    user = User.objects.get(pk=user)

    controller.read_file(user, file_path)


@celery_app.task()
def load_articles(user_id, file_path):
    try:
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        user = User.objects.first()

    xmltree = xml_utils.get_xml_tree(file_path)

    pids = ArticleIds(xmltree=xmltree).data
    pid_v2 = pids.get("v2")
    pid_v3 = pids.get("v3")

    try:
        article = models.Article.objects.get(Q(pid_v2=pid_v2) | Q(pid_v3=pid_v3))
    except models.Article.DoesNotExist:
        article = models.Article()
    try:
        article_utils.set_pids(xmltree=xmltree, article=article)
        article.journal = article_utils.get_journal(xmltree=xmltree)
        article_utils.set_date_pub(xmltree=xmltree, article=article)
        article.article_type = article_utils.get_or_create_article_type(
            xmltree=xmltree, user=user
        )
        article.issue = article_utils.get_or_create_issues(xmltree=xmltree, user=user)
        article_utils.set_first_last_page(xmltree=xmltree, article=article)
        article_utils.set_elocation_id(xmltree=xmltree, article=article)
        article.save()
        article.doi.set(article_utils.get_or_create_doi(xmltree=xmltree, user=user))
        article.license.set(article_utils.get_or_create_licenses(xmltree=xmltree, user=user))
        article.researchers.set(
            article_utils.get_or_create_researchers(xmltree=xmltree, user=user)
        )
        article.languages.add(
            article_utils.get_or_create_main_language(xmltree=xmltree, user=user)
        )
        article.keywords.set(article_utils.get_or_create_keywords(xmltree=xmltree, user=user))
        article.toc_sections.set(
            article_utils.get_or_create_toc_sections(xmltree=xmltree, user=user)
        )
        article.fundings.set(article_utils.get_or_create_fundings(xmltree=xmltree, user=user))
        article.titles.set(article_utils.get_or_create_titles(xmltree=xmltree, user=user))
    except (DataError, TypeError) as e:
        raise ArticleSaveError(e)


@celery_app.task(bind=True, name=_("load_preprints"))
def load_preprint(self, user_id, oai_pmh_preprint_uri):
    user = _get_user(self.request, user_id=user_id)
    ## fazer filtro para não coletar tudo sempre
    harvest_preprints(oai_pmh_preprint_uri, user)
