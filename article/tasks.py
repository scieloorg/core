from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import DataError
from sickle import Sickle

from article import models
from article.preprint import utils as preprint
from config import celery_app

from . import controller
from article.sources import xmlsps

User = get_user_model()


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

    xmlsps.load_article(file_path, user)


@celery_app.task()
def load_preprint(user_id):
    URL = "https://preprints.scielo.org/index.php/scielo/oai"

    try:
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        user = User.objects.first()
    ## TODO
    ## fazer filtro para não coletar tudo sempre
    sickle = Sickle(URL)
    recs = sickle.ListRecords(metadataPrefix="oai_dc")
    for rec in recs:
        article_info = preprint.get_info_article(rec)
        identifier = preprint.get_doi(article_info["identifier"])
        doi = preprint.get_or_create_doi(doi=identifier, user=user)

        article = models.Article.get_or_create(
            doi=doi,
            pid_v2=None,
            user=user,
            fundings=None,
        )
        try:
            preprint.set_dates(article=article, date=article_info.get("date"))
            article.titles.set(
                preprint.get_or_create_titles(
                    titles=article_info.get("title"), user=user
                )
            )
            article.researchers.set(
                preprint.get_or_create_researches(
                    authors=article_info.get("authors"),
                )
            )
            article.keywords.set(
                preprint.get_or_create_keyword(
                    keywords=article_info.get("subject"), user=user
                )
            )
            article.license.set(
                preprint.get_or_create_license(
                    rights=article_info.get("rights"), user=user
                )
            )
            article.abstracts.set(
                preprint.get_or_create_abstracts(
                    description=article_info.get("description"), user=user
                )
            )
            article.languages.add(
                preprint.get_or_create_language(
                    lang=article_info.get("language"), user=user
                )
            )
            article.publisher = preprint.get_publisher(
                publisher=article_info.get("publisher")
            )
            article.save()
        except (DataError, TypeError) as e:
            raise ArticleSaveError(e)
