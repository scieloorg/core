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
        journals = Journal.objects.filter(
            article__pub_date_year=year, scielojournal__issn_scielo=issn_scielo
        )

        if journals:
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
                case _:
                    raise ValueError("No match found")

            for journal in journals:
                kwargs["journal_id"] = journal.id
                func_partial.apply_async(kwargs=kwargs)
    else:
        raise ValueError(
            "Parameters 'year' and 'issn_scielo' are required for execution."
        )


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
                    csv_writer.writerow(
                        [
                            article.pid_v2,
                            article.journal.short_title,
                            article.issue.volume,
                            article.issue.number,
                            article.journal.scielojournal_set.all()[0].issn_scielo,
                            keyword.text,
                            keyword.language.name,
                            keyword.language.code2,
                        ]
                    )

            j = Journal.objects.get(id=journal_id)
            report_csv = ReportCSV.create_or_update(
                journal=j,
                title="Keywords",
                publication_year=year,
                columns=columns,
                csv_data=csv_data,
                user=user,
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
                    csv_writer.writerow(
                        [
                            article.pid_v2,
                            article.journal.short_title,
                            article.issue.volume,
                            article.issue.number,
                            article.issue.supplement,
                            abstract.plain_text,
                            abstract.language.name,
                            abstract.language.code2,
                        ]
                    )

            j = Journal.objects.get(id=journal_id)
            report_csv = ReportCSV.create_or_update(
                journal=j,
                title="Abstracts",
                publication_year=year,
                columns=columns,
                csv_data=csv_data,
                user=user,
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


@celery_app.task(bind=True)
def task_report_pid_v2_amissue(
    self, collection_acron3, journal_acron_list=None, username=None, user_id=None
):
    """
    Gera, para cada periódico da coleção, o CSV dos artigos sem AMArticle na
    coleção, com as inconsistências entre o pid_v2 e o PID do fascículo
    (AMIssue) (ver report.pid_v2_amissue)

    O CSV fica em ReportCSV (título "pid_v2 x AMIssue <coleção>"); periódicos
    sem artigos a relatar não geram CSV. Retorna o total de artigos por
    periódico.
    """
    from django.core.files.base import ContentFile

    from journal.models import SciELOJournal
    from report import pid_v2_amissue

    user = _get_user(self.request, username=username, user_id=user_id)
    scielo_journals = SciELOJournal.objects.filter(
        collection__acron3=collection_acron3, journal__isnull=False
    ).select_related("collection", "journal")
    if journal_acron_list:
        scielo_journals = scielo_journals.filter(journal_acron__in=journal_acron_list)

    totals = {}
    for scielo_journal in scielo_journals:
        try:
            rows = list(pid_v2_amissue.get_rows(scielo_journal))
            if not rows:
                continue
            with StringIO() as csv_data:
                csv_writer = csv.DictWriter(csv_data, fieldnames=pid_v2_amissue.COLUMNS)
                csv_writer.writeheader()
                csv_writer.writerows(rows)
                content = ContentFile(csv_data.getvalue().encode("utf-8"))
            ReportCSV.create_or_update(
                journal=scielo_journal.journal,
                publication_year=None,
                title=f"pid_v2 x AMIssue {collection_acron3}",
                columns={"columns": pid_v2_amissue.COLUMNS},
                csv_data=content,
                user=user,
            )
            totals[scielo_journal.journal_acron] = len(rows)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "task": "report.tasks.task_report_pid_v2_amissue",
                    "collection_acron3": collection_acron3,
                    "journal_acron": scielo_journal.journal_acron,
                },
            )
    return totals
