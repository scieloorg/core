import csv
import logging
import sys

from django.db.models import Q
from packtools.sps.formats.am import am

from core.utils import date_utils
from core.mongodb import write_to_db
from institution.models import Sponsor
from tracker.models import UnexpectedEvent

from .models import Article, ArticleExport, ArticleFunding


def load_financial_data(row, user):
    article_findings = []
    for institution in row.get("funding_source").split(","):
        sponsor = Sponsor.get_or_create(
            user=user,
            name=institution,
            acronym=None,
            level_1=None,
            level_2=None,
            level_3=None,
            location=None,
            official=None,
            is_official=None,
            url=None,
            institution_type=None,
        )
        article_findings.append(
            ArticleFunding.get_or_create(
                award_id=row.get("award_id"), funding_source=sponsor, user=user
            )
        )
    article = Article.get_or_create(
        pid_v2=row.get("pid_v2"), fundings=article_findings, user=user
    )

    return article


def read_file(user, file_path):
    with open(file_path, "r") as csvfile:
        data = csv.DictReader(csvfile)
        for row in data:
            logging.debug(row)
            load_financial_data(row, user)


def export_article_to_articlemeta(
    pid_v3,
    collections=[],
    force_update=True,
    user=None,
    client=None,
) -> bool:
    """
    Convert an article to ArticleMeta format and write it to MongoDB.

    Args:
        pid_v3 (str): The PID v3 of the article to export.
        collections (list): List of collection names to associate with the article.
        force_update (bool): Whether to force update the export. Defaults to True.
        user (User): The user associated with the export. Defaults to None.
        client (MongoDB client): MongoDB client instance. Defaults to None.

    Returns:
        bool: True if the export was successful, False otherwise.
    """
    if not pid_v3:
        logging.error("No pid_v3 or pid_v2 provided for export.")
        return False

    try:
        article = Article.get(pid_v3=pid_v3)
    except Article.DoesNotExist:
        logging.error(f"Article with pid_v3 {pid_v3} does not exist.")
        return False
    
    external_data = {
        'collection': '',
        "created_at": article.created.strftime("%Y-%m-%d"),
        "document_type": "",
        "processing_date": article.updated,
        "publication_date": "",
        "publication_year": "",
        'version': 'xml' # Assuming the version is always 'xml'
    }

    # Build ArticleMeta format for the article
    try:
        article_data = am.build(article.xmltree, external_data)
    except Exception as e:
        logging.error(f"Error building ArticleMeta format for article {pid_v3}: {e}")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "export_article_to_articlemeta",
                "pid_v3": pid_v3,
                "force_update": force_update,
                "stage": "building articlemeta format for article"
            },
        )
        return False
    
    # Restrict collections if provided
    cols = [c for c in article.collections if c.acron3 in collections] if collections else article.collections

    for col in cols:
        if not force_update and ArticleExport.is_exported(article, 'articlemeta', col):
            logging.info(f"Article {pid_v3} already exported to ArticleMeta in collection {col}.")
            continue

        external_data.update({'collection': col.acron3})
        article_data.update(external_data)

        # Build ArticleMeta format for the issue
        try:
            issue_data = article.issue.articlemeta_format(col.acron3)
        except Exception as e:
            logging.error(f"Error converting issue data for ArticleMeta export for article {pid_v3}: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "export_article_to_articlemeta",
                    "pid_v3": pid_v3,
                    "force_update": force_update,
                    "stage": "building articlemeta format for issue"
                }
            )

            issue_data = {}

        # Update ArticleMeta format with issue and journal data
        try:
            # Article data
            article_data['code'] = article_data['article']['code']
            article_data['document_type'] = article.article_type
            article_data['publication_date'] = article.pub_date
            article_data['publication_year'] = article.pub_date_year

            # Issue data
            article_data['code_issue'] = issue_data['code']
            article_data['issue'] = issue_data['issue']
            
            # Journal data
            article_data['code_title'] = [x for x in issue_data['code_title'] if x is not None]
            article_data['title'] = issue_data['title']
        except Exception as e:
            logging.error(f"Error updating ArticleMeta format with issue and journal data for article with pid_v3 {pid_v3}: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "export_article_to_articlemeta",
                    "pid_v3": pid_v3,
                    "force_update": force_update,
                    "stage": "updating articlemeta format with issue and journal data"
                }
            )

        # Export the article to ArticleMeta
        try:
            success = write_to_db(
                data=article_data, 
                database="articlemeta", 
                collection="articles", 
                force_update=force_update,
                client=client,
            )

            # Mark the article as exported to ArticleMeta in the collection
            if success:
                ArticleExport.mark_as_exported(article, 'articlemeta', col, user)
        except Exception as e:
            logging.error(f"Error writing article {pid_v3} to ArticleMeta database: {e}")
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "operation": "export_article_to_articlemeta",
                    "pid_v3":pid_v3,
                    "force_update":force_update,
                    "stage":"writing article to articlemeta database"
                }
            )
        
    return True
