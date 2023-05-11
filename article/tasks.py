from article import models
from config import celery_app
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.utils import DataError

from packtools.sps.models.article_ids import ArticleIds
from packtools.sps.utils import xml_utils
from . import utils
from .utils import ArticleSaveError

from . import controller

User = get_user_model()


@celery_app.task()
def load_funding_data(user, file_path):
    user = User.objects.get(pk=user)

    controller.read_file(user, file_path)


@celery_app.task()
def load_articles(user=None):
    user = user or User.objects.first()

    # Xml usado para testes.
    xmltree = xml_utils.get_xml_tree("article/fixtures/0034-8910-rsp-48-2-0249.xml")
    pid_v2 = ArticleIds(xmltree=xmltree).data.get("v2")
    pid_v3 = ArticleIds(xmltree=xmltree).data.get("v3")
    try:
        article = models.Article.objects.get(Q(pid_v2=pid_v2) | Q(pid_v3=pid_v3))
    except models.Article.DoesNotExist:
        article = models.Article()
    try:
        utils.set_pids(xmltree=xmltree, article=article)
        article.journal = utils.get_journal(xmltree=xmltree)
        utils.set_date_pub(xmltree=xmltree, article=article)
        article.article_type = utils.get_or_create_article_type(
            xmltree=xmltree, user=user
        )
        article.issue = utils.get_or_create_issues(xmltree=xmltree, user=user)
        utils.set_first_last_page(xmltree=xmltree, article=article)
        utils.set_elocation_id(xmltree=xmltree, article=article)
        article.save()
        article.doi.set(utils.get_or_create_doi(xmltree=xmltree, user=user))
        article.license.set(utils.get_or_create_licenses(xmltree=xmltree, user=user))
        article.researchers.set(
            utils.get_or_create_researchers(xmltree=xmltree, user=user)
        )
        article.keywords.set(utils.get_or_create_keywords(xmltree=xmltree, user=user))
        article.toc_sections.set(
            utils.get_or_create_toc_sections(xmltree=xmltree, user=user)
        )
        article.fundings.set(utils.get_or_create_fundings(xmltree=xmltree, user=user))
        article.titles.set(utils.get_or_create_titles(xmltree=xmltree, user=user))
    except (DataError, TypeError) as e:
        raise ArticleSaveError(e)
