import logging
import sys
from datetime import datetime, timezone

import requests
from django.utils.translation import gettext_lazy as _

from config import celery_app
from core.utils.utils import _get_user
from tracker.models import UnexpectedEvent

logger = logging.getLogger(__name__)


def _deposit_xml_to_crossref(xml_content, filename, config):
    """
    Submits the given XML content to the Crossref deposit API.

    Parameters
    ----------
    xml_content : bytes or str
        The XML content to deposit.
    filename : str
        The filename to send as part of the multipart upload.
    config : CrossRefConfiguration
        The configuration object containing API credentials and deposit URL.

    Returns
    -------
    requests.Response
        The HTTP response from the Crossref API.
    """
    if not config.username or not config.password:
        raise ValueError("Crossref username and password are required to perform a deposit")

    if isinstance(xml_content, str):
        xml_content = xml_content.encode("utf-8")

    response = requests.post(
        config.deposit_url,
        data={
            "operation": "doMDUpload",
            "login_id": config.username,
            "login_passwd": config.password,
        },
        files={"fname": (filename, xml_content, "text/xml")},
        timeout=60,
    )
    response.raise_for_status()
    return response


@celery_app.task(bind=True)
def task_deposit_doi_to_crossref(
    self,
    article_id=None,
    user_id=None,
    username=None,
):
    """
    Performs the DOI deposit for a single article to Crossref.

    Parameters
    ----------
    article_id : int
        The primary key of the Article to deposit.
    user_id : int, optional
        ID of the user triggering the deposit.
    username : str, optional
        Username of the user triggering the deposit.
    """
    from article.models import Article, ArticleFormat
    from doi_manager.models import CrossRefConfiguration, CrossRefDeposit

    deposit = None
    try:
        if not article_id:
            raise ValueError("task_deposit_doi_to_crossref requires article_id")

        article = Article.objects.get(pk=article_id)
        user = _get_user(self.request, username=username, user_id=user_id)

        # Ensure the crossref format has been generated
        crossref_format = None
        try:
            crossref_format = ArticleFormat.objects.get(
                article=article, format_name="crossref"
            )
        except ArticleFormat.MultipleObjectsReturned:
            crossref_format = ArticleFormat.objects.filter(
                article=article, format_name="crossref"
            ).last()
        except ArticleFormat.DoesNotExist:
            pass

        if crossref_format is None or not crossref_format.file:
            ArticleFormat.generate_formats(user, article)
            try:
                crossref_format = ArticleFormat.objects.get(
                    article=article, format_name="crossref"
                )
            except (ArticleFormat.DoesNotExist, ArticleFormat.MultipleObjectsReturned):
                crossref_format = ArticleFormat.objects.filter(
                    article=article, format_name="crossref"
                ).last()

        if crossref_format is None or not crossref_format.file:
            raise ValueError(
                f"Could not generate or find crossref format for article {article_id}"
            )

        # Determine the DOI prefix for configuration lookup
        prefix = None
        for doi in article.doi.all():
            if doi.value and "/" in doi.value:
                prefix = doi.value.split("/")[0]
                break

        if not prefix:
            raise ValueError(
                f"Article {article_id} has no DOI with a prefix, cannot deposit to Crossref"
            )

        config = CrossRefConfiguration.objects.get(prefix=prefix)

        deposit = CrossRefDeposit()
        deposit.article = article
        deposit.status = CrossRefDeposit.DEPOSIT_STATUS_PENDING
        deposit.creator = user
        deposit.save()

        # Read the crossref XML file
        with crossref_format.file.open("rb") as f:
            xml_content = f.read()

        filename = crossref_format.file.name.split("/")[-1]

        deposit.status = CrossRefDeposit.DEPOSIT_STATUS_SUBMITTED
        deposit.submission_date = datetime.now(timezone.utc)
        deposit.updated_by = user
        deposit.save()

        response = _deposit_xml_to_crossref(xml_content, filename, config)

        deposit.status = CrossRefDeposit.DEPOSIT_STATUS_SUCCESS
        deposit.response = response.text
        deposit.updated_by = user
        deposit.save()

        logger.info(
            "Crossref deposit successful for article %s: %s",
            article_id,
            response.status_code,
        )
        return {"article_id": article_id, "status": "success", "response": response.text}

    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if deposit is not None:
            try:
                deposit.status = CrossRefDeposit.DEPOSIT_STATUS_FAILED
                deposit.detail = {"error": str(exception)}
                deposit.save()
            except Exception:
                pass
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "doi_manager.tasks.task_deposit_doi_to_crossref",
                "article_id": article_id,
            },
        )


@celery_app.task(bind=True)
def task_deposit_doi_to_crossref_for_articles(
    self,
    user_id=None,
    username=None,
    article_id_list=None,
    journal_acron_list=None,
    from_pub_year=None,
    until_pub_year=None,
    from_updated_date=None,
    until_updated_date=None,
):
    """
    Schedules DOI deposit for a batch of articles.

    Articles can be specified directly via ``article_id_list`` or filtered
    by journal acronym and/or publication year range.  Each matching article
    is dispatched as an individual ``task_deposit_doi_to_crossref`` sub-task.

    Parameters
    ----------
    user_id : int, optional
    username : str, optional
    article_id_list : list of int, optional
        Explicit list of article primary keys.
    journal_acron_list : list of str, optional
        Filter articles by journal acronym.
    from_pub_year : int or str, optional
    until_pub_year : int or str, optional
    from_updated_date : str, optional  (ISO 8601)
    until_updated_date : str, optional (ISO 8601)
    """
    from article.models import Article
    from django.db.models import Q

    try:
        user = _get_user(self.request, username=username, user_id=user_id)

        if article_id_list:
            articles = Article.objects.filter(pk__in=article_id_list)
        else:
            articles = Article.objects.all()

            if journal_acron_list:
                articles = articles.filter(
                    journal__scielojournal__journal_acron__in=journal_acron_list
                ).distinct()

            if from_pub_year:
                articles = articles.filter(
                    Q(issue__year__gte=str(from_pub_year)) | Q(pub_date_year__gte=str(from_pub_year))
                )
            if until_pub_year:
                articles = articles.filter(
                    Q(issue__year__lte=str(until_pub_year)) | Q(pub_date_year__lte=str(until_pub_year))
                )
            if from_updated_date:
                articles = articles.filter(updated__gte=from_updated_date)
            if until_updated_date:
                articles = articles.filter(updated__lte=until_updated_date)

        # Only deposit articles that have a DOI
        articles = articles.filter(doi__isnull=False).distinct()

        count = 0
        for article in articles.iterator():
            task_deposit_doi_to_crossref.delay(
                article_id=article.pk,
                user_id=user.id,
                username=user.username,
            )
            count += 1

        logger.info("Scheduled Crossref deposit for %d articles", count)
        return {"scheduled": count}

    except Exception as exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=exception,
            exc_traceback=exc_traceback,
            detail={
                "task": "doi_manager.tasks.task_deposit_doi_to_crossref_for_articles",
                "article_id_list": article_id_list,
                "journal_acron_list": journal_acron_list,
            },
        )
        raise
