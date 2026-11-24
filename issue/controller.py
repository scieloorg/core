import json
import logging
import sys
import traceback

from django.db.models import Count, F, Q

from core.mongodb import write_item
from issue.articlemeta.loader import create_issue_from_am_issue
from issue.models import AMIssue, Issue, IssueExporter
from tracker.models import UnexpectedEvent


def export_issue_to_articlemeta(
    user,
    issue,
    collection_acron_list=None,
    force_update=None,
    version=None,
):
    try:
        events = None
        if not issue:
            raise ValueError("export_issue_to_articlemeta requires issue")
        legacy_keys_items = list(issue.get_legacy_keys(collection_acron_list, is_active=True))
        if not legacy_keys_items:
            UnexpectedEvent.create(
                exception=ValueError("No legacy keys found for issue"),
                detail={
                    "operation": "export_issue_to_articlemeta",
                    "issue": str(issue),
                    "collection_acron_list": collection_acron_list,
                    "force_update": force_update,
                    "events": events,
                },
            )
            return
        for legacy_keys in legacy_keys_items:
            try:
                exporter = None
                response = None
                events = []
                col = legacy_keys.get("collection")
                pid = legacy_keys.get("pid")
                logging.info(
                    (user, issue, "articlemeta", pid, col, version, force_update)
                )
                events.append("check articlemeta exportation demand")
                exporter = IssueExporter.get_demand(
                    user, issue, "articlemeta", pid, col, version, force_update
                )
                if not exporter:
                    # não encontrou necessidade de exportar
                    continue

                events.append("building articlemeta format for issue")
                issue_data = issue.articlemeta_format(col.acron3)

                try:
                    json.dumps(issue_data)
                except Exception as e:
                    logging.exception(e)
                    response = str(issue_data)
                    raise e

                events.append("writing issue to articlemeta database")
                response = write_item("issues", issue_data)
                exporter.finish(
                    user,
                    completed=True,
                    events=events,
                    response=response,
                    errors=None,
                    exceptions=None,
                )
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if exporter:
                    exporter.finish(
                        user,
                        completed=False,
                        events=events,
                        response=response,
                        errors=None,
                        exceptions=traceback.format_exc(),
                    )
                else:
                    UnexpectedEvent.create(
                        exception=e,
                        exc_traceback=exc_traceback,
                        detail={
                            "operation": "export_article_to_articlemeta",
                            "issue": str(issue),
                            "collection": str(col),
                            "events": events,
                            "traceback": traceback.format_exc(),
                        },
                    )

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "operation": "export_issue_to_articlemeta",
                "issue": issue,
                "collection_acron_list": collection_acron_list,
                "force_update": force_update,
                "events": events,
            },
        )


def bulk_export_issues_to_articlemeta(
    user=None,
    collection_acron_list=None,
    journal_acron_list=None,
    publication_year=None,
    volume=None,
    number=None,
    supplement=None,
    from_date=None,
    until_date=None,
    days_to_go_back=None,
    force_update=None,
    version=None,
):
    """
    Export issues to ArticleMeta Database with flexible filtering.

    Args:
        user: User object for authentication
        collection_acron_list: List of collections acronyms (e.g., ["scl", "mex"])
        journal_acron_list: List of journal acronyms to filter
        publication_year: Filter by publication year
        volume: Filter by volume number
        number: Filter by issue number
        supplement: Filter by supplement
        from_date: Export issues modified from this date
        until_date: Export issues modified until this date
        days_to_go_back: Export issues modified from this number of days ago
        force_update: Force update existing records
        version: Version identifier for export
    """
    try:
        queryset = Issue.select_issues(
            collection_acron_list=collection_acron_list,
            journal_acron_list=journal_acron_list,
            publication_year=publication_year,
            volume=volume,
            number=number,
            supplement=supplement,
            from_date=from_date,
            until_date=until_date,
            days_to_go_back=days_to_go_back,
        )
        if not queryset.exists():
            UnexpectedEvent.create(
                exception=ValueError("No issues found for the given filters"),
                detail={
                    "function": "bulk_export_issues_to_articlemeta",
                    "collection_acron_list": collection_acron_list,
                    "journal_acron_list": journal_acron_list,
                    "publication_year": publication_year,
                    "volume": volume,
                    "number": number,
                    "supplement": supplement,
                    "from_date": str(from_date) if from_date else None,
                    "until_date": str(until_date) if until_date else None,
                    "days_to_go_back": days_to_go_back,
                    "force_update": force_update,
                },
            )
            return
        for issue in queryset.iterator():
            try:
                export_issue_to_articlemeta(
                    user,
                    issue=issue,
                    collection_acron_list=collection_acron_list,
                    force_update=force_update,
                    version=version,
                )
            except Exception as e:
                # Registra erro do issue mas continua processando outros
                exc_type, exc_value, exc_traceback = sys.exc_info()
                UnexpectedEvent.create(
                    exception=e,
                    exc_traceback=exc_traceback,
                    detail={
                        "function": "bulk_export_issues_to_articlemeta",
                        "issue_id": issue.id,
                        "journal_acron": getattr(issue, "journal_acron", None),
                        "publication_year": getattr(issue, "publication_year", None),
                        "volume": getattr(issue, "volume", None),
                        "number": getattr(issue, "number", None),
                        "supplement": getattr(issue, "supplement", None),
                        "force_update": force_update,
                    },
                )
                continue
                
    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        UnexpectedEvent.create(
            exception=e,
            exc_traceback=exc_traceback,
            detail={
                "function": "bulk_export_issues_to_articlemeta",
                "collection_acron_list": collection_acron_list,
                "journal_acron_list": journal_acron_list,
                "publication_year": publication_year,
                "volume": volume,
                "number": number,
                "supplement": supplement,
                "from_date": str(from_date) if from_date else None,
                "until_date": str(until_date) if until_date else None,
                "days_to_go_back": days_to_go_back,
                "force_update": force_update,
            },
        )
        raise

def migrate_issue_legacy_keys(
    user,
    collection_acron_list=None,
    journal_pid_list=None,
    publication_year=None,
    link_am_issues=True,
    fix_issue_pid_suffix=True,
    force_update=False,
):
    """
    Garante o relacionamento entre Issue e AMIssue (issue_pid por coleção)
    para os registros criados antes da existência do AMIssue.

    Etapas:
    1. AMIssue migrados (com data ou url) sem new_record são associados ao
       Issue correspondente (identificado por journal, ano, volume, número e
       suplemento), criando o Issue se necessário.
    2. issue_pid_suffix é recalculado por volume/número/suplemento quando
       ausente ou diferente da regra (ex.: Issues migrados, em que o valor
       foi copiado do pid atribuído manualmente em uma das coleções).
       Os pids já estabelecidos não são alterados: estão no AMIssue.
    3. Issues sem AMIssue em alguma das coleções do periódico recebem um
       issue_pid gerado automaticamente para cada coleção faltante.

    A etapa 1 é executada antes da 3 para que os pids migrados prevaleçam
    sobre os gerados, e a 2 antes da 3 para que os pids gerados usem a
    ordem calculada pela regra.

    Returns:
        dict: estatísticas da execução
    """
    stats = {
        "am_issues_linked": 0,
        "am_issues_errors": 0,
        "issue_pid_suffix_fixed": 0,
        "issues_processed": 0,
        "issues_errors": 0,
    }

    if link_am_issues:
        am_issues = AMIssue.objects.filter(
            Q(data__isnull=False) | Q(url__isnull=False),
            new_record__isnull=True,
        )
        if collection_acron_list:
            am_issues = am_issues.filter(collection__acron3__in=collection_acron_list)
        if journal_pid_list:
            q = Q()
            for journal_pid in journal_pid_list:
                q |= Q(pid__startswith=journal_pid)
            am_issues = am_issues.filter(q)
        if publication_year:
            am_issues = am_issues.filter(pid__regex=rf"^.{{9}}{publication_year}")

        for am_issue in am_issues.iterator():
            if create_issue_from_am_issue(user, am_issue):
                stats["am_issues_linked"] += 1
            else:
                stats["am_issues_errors"] += 1

    params = {}
    if collection_acron_list:
        params["journal__scielojournal__collection__acron3__in"] = collection_acron_list
    if journal_pid_list:
        params["journal__scielojournal__issn_scielo__in"] = journal_pid_list
    if publication_year:
        params["year"] = publication_year
    issue_ids = Issue.objects.filter(
        journal__isnull=False, year__isnull=False, **params
    ).values("id")

    if fix_issue_pid_suffix:
        for issue in (
            Issue.objects.filter(id__in=issue_ids)
            .only("id", "number", "supplement", "issue_pid_suffix")
            .iterator()
        ):
            suffix = issue.generate_issue_pid_suffix()
            if suffix != issue.issue_pid_suffix:
                # update evita save(), que geraria pids antes da etapa 3
                Issue.objects.filter(pk=issue.pk).update(issue_pid_suffix=suffix)
                stats["issue_pid_suffix_fixed"] += 1

    issues = Issue.objects.filter(id__in=issue_ids).select_related("journal")
    if not force_update:
        # apenas issues com menos coleções com AMIssue do que coleções do periódico
        issues = issues.annotate(
            n_keys=Count("legacy_issue__collection", distinct=True),
            n_collections=Count("journal__scielojournal__collection", distinct=True),
        ).filter(n_keys__lt=F("n_collections"))

    for issue in issues.iterator():
        try:
            stats["issues_processed"] += 1
            issue.create_legacy_keys(user=user, force_update=force_update)
        except Exception as e:
            stats["issues_errors"] += 1
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "function": "migrate_issue_legacy_keys",
                    "issue_id": issue.id,
                    "force_update": force_update,
                },
            )
    return stats
