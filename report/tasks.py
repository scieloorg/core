import sys
import csv
from io import StringIO
from django.contrib.auth import get_user_model

from article.models import Article
from config import celery_app
from core.utils.utils import _get_user
from journal.models import Journal
from report.models import ReportCSV
from tracker.models import UnexpectedEvent


@celery_app.task(bind=True)
def report_csv_generator(self, year, issn_scielo, type_report, username):
    if year and issn_scielo:
        journals = Journal.objects.filter(article__pub_date_year=year, scielojournal__issn_scielo=issn_scielo)
    
        match type_report:
            case "article":
                kwargs = dict(
                    year=year,
                    columns={
                        "columns": [
                            "pid_v2",
                            "short_title",
                            "volume",
                            "number",
                            "issn_scielo",
                            "keyword",
                            "language",
                            "code_language",
                        ]
                    },
                    username=username,
                )
                func_partial = generate_report_csv_articles
            case "article_funding":
                pass
            case "abstract":
                kwargs = dict(
                    year=year,
                    columns={
                        "columns": [
                            "pid_v2",
                            "short_title",
                            "volume",
                            "number",
                            "supplement",
                            "abstract",
                            "language",
                            "code_language",
                        ]
                    },
                    username=username,
                )
                func_partial = generate_report_csv_abstract

        for journal in journals:
            kwargs["journal_id"] = journal.id
            func_partial.apply_async(kwargs=kwargs)
    else: 
        raise ValueError("Parameters 'year' and 'issn_scielo' are required for execution.")


@celery_app.task(bind=True)
def generate_report_csv_articles(self, journal_id, year, columns, username):
    user = _get_user(self.request, username)
    articles = Article.objects.filter(journal__id=journal_id, pub_date_year=year)
    try:
        with StringIO() as csv_data:
            csv_writer = csv.writer(csv_data)
            csv_writer.writerow(columns.get("columns"))

            for article in articles:
                for keyword in article.keywords.all():
                    csv_writer.writerow([
                        article.pid_v2,
                        article.journal.short_title,
                        article.issue.volume,
                        article.issue.number,
                        article.journal.scielojournal_set.all()[0].issn_scielo,
                        keyword.text,
                        keyword.language.name,
                        keyword.language.code2,
                    ])
            
            j = Journal.objects.get(id=journal_id)
            report_csv = ReportCSV.create_or_update(
                journal=j,
                title="Keywords",
                publication_year=year,
                columns=columns,
                csv_data=csv_data,
                user=user
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "report.tasks.generate_report_csv_articles",
                "journal_id": journal_id,
                "year": year,
            },
        )        


@celery_app.task(bind=True)
def generate_report_csv_abstract(self, journal_id, year, columns, username):
    user = _get_user(self.request, username)
    articles = Article.objects.filter(journal__id=journal_id, pub_date_year=year)
    try:
        with StringIO() as csv_data:
            csv_writer = csv.writer(csv_data)
            csv_writer.writerow(columns.get("columns"))

            for article in articles:
                for abstract in article.abstracts.all():
                    csv_writer.writerow([
                        article.pid_v2,
                        article.journal.short_title,
                        article.issue.volume,
                        article.issue.number,
                        article.issue.supplement,
                        abstract.plain_text,
                        abstract.language.name,
                        abstract.language.code2,
                    ])
            
            j = Journal.objects.get(id=journal_id)
            report_csv = ReportCSV.create_or_update(
                journal=j,
                title="Abstracts",
                publication_year=year,
                columns=columns,
                csv_data=csv_data,
                user=user
            )
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "task": "report.tasks.generate_report_csv_abstract",
                "journal_id": journal_id,
                "year": year,
            },
        )  
