"""
Inconsistências entre o pid_v2 do artigo e o PID do fascículo (AMIssue) na
coleção (ver https://github.com/scieloorg/core/issues/1507)

O pid_v2 contém o PID do fascículo (pid_v2[1:18]: ISSN + ano + sufixo). O
AMArticle da coleção só é criado (load_article) se o PID do AMIssue estiver
contido no pid_v2; sem AMArticle, a exportação para o AM falha com
"No legacy keys found for article".

O relatório não corrige nada: lista os artigos do periódico sem AMArticle
na coleção e classifica cada um, para apoiar a decisão sobre a correção.
"""

from collections import defaultdict

from article.models import AMArticle, Article
from core import choices as core_choices
from issue.models import AMIssue, IssueExporter

# o fascículo do artigo não tem AMIssue na coleção
ISSUE_WITHOUT_AMISSUE = "issue_without_amissue"
# o fascículo tem AMIssue na coleção, diferente do PID contido no pid_v2
AMISSUE_DIFFERS = "amissue_differs"
# o AMIssue coincide com o PID contido no pid_v2: falta só reprocessar o
# artigo (create_legacy_keys) para criar o AMArticle
AMISSUE_MATCHES = "amissue_matches"
# artigos do mesmo fascículo têm PIDs de fascículo diferentes no pid_v2
PREFIXES_DIFFER_IN_ISSUE = "prefixes_differ_in_issue"
# o PID de fascículo do pid_v2 aparece em artigos de outros fascículos
PREFIX_IN_OTHER_ISSUES = "prefix_in_other_issues"
# o PID de fascículo do pid_v2 é o AMIssue de outro fascículo na coleção
PREFIX_IS_OTHER_ISSUE_PID = "prefix_is_other_issue_pid"
# o fascículo foi exportado para o AM com código diferente do pid_v2
ISSUE_EXPORTED_WITH_OTHER_CODE = "issue_exported_with_other_code"
# o ISSN do pid_v2 difere do issn_scielo do periódico na coleção
PREFIX_ISSN_DIFFERS = "prefix_issn_differs"
# o ano do pid_v2 difere do ano do fascículo
PREFIX_YEAR_DIFFERS = "prefix_year_differs"
ARTICLE_WITHOUT_PID_V2 = "article_without_pid_v2"
ARTICLE_WITHOUT_ISSUE = "article_without_issue"

COLUMNS = [
    "collection",
    "journal_acron",
    "issn_scielo",
    "issue_id",
    "issue_year",
    "volume",
    "number",
    "supplement",
    "issue_folder",
    "amissue_pids",
    "exported_issue_codes",
    "pid_v3",
    "pid_v2",
    "pid_v2_issue_pid",
    "categories",
]


def get_issue_pid(pid_v2):
    """PID do fascículo contido no pid_v2 (S + 17 caracteres + 5 dígitos)"""
    if pid_v2 and len(pid_v2) == 23:
        return pid_v2[1:18]


def get_rows(scielo_journal):
    """
    Artigos do periódico sem AMArticle na coleção do scielo_journal, com
    as categorias de inconsistência (ver constantes do módulo)
    """
    collection = scielo_journal.collection
    journal = scielo_journal.journal
    issn_scielo = scielo_journal.issn_scielo

    articles = list(
        Article.objects.filter(journal=journal)
        .select_related("issue")
        .order_by("issue__year", "issue_id", "pid_v2")
    )
    with_am_article = set(
        AMArticle.objects.filter(
            collection=collection, new_record__journal=journal
        ).values_list("new_record_id", flat=True)
    )

    amissue_pids = defaultdict(set)
    amissue_owner = {}
    for issue_id, pid in AMIssue.objects.filter(
        collection=collection, new_record__journal=journal
    ).values_list("new_record_id", "pid"):
        amissue_pids[issue_id].add(pid)
        amissue_owner[pid] = issue_id

    exported_codes = defaultdict(set)
    for issue_id, pid in IssueExporter.objects.filter(
        collection=collection,
        parent__journal=journal,
        status=core_choices.EXPORTATION_STATUS_DONE,
    ).values_list("parent_id", "pid"):
        exported_codes[issue_id].add(pid)

    # PIDs de fascículo contidos no pid_v2 de todos os artigos do periódico
    prefixes_by_issue = defaultdict(set)
    issues_by_prefix = defaultdict(set)
    for article in articles:
        prefix = get_issue_pid(article.pid_v2)
        if prefix and article.issue_id:
            prefixes_by_issue[article.issue_id].add(prefix)
            issues_by_prefix[prefix].add(article.issue_id)

    for article in articles:
        if article.id in with_am_article:
            continue
        issue = article.issue
        prefix = get_issue_pid(article.pid_v2)
        categories = []
        if not prefix:
            categories.append(ARTICLE_WITHOUT_PID_V2)
        if not issue:
            categories.append(ARTICLE_WITHOUT_ISSUE)
        if issue:
            pids = amissue_pids.get(issue.id) or set()
            if not pids:
                categories.append(ISSUE_WITHOUT_AMISSUE)
            elif prefix and prefix not in pids:
                categories.append(AMISSUE_DIFFERS)
            elif prefix:
                categories.append(AMISSUE_MATCHES)
            if len(prefixes_by_issue.get(issue.id) or ()) > 1:
                categories.append(PREFIXES_DIFFER_IN_ISSUE)
            if prefix:
                if issues_by_prefix[prefix] - {issue.id}:
                    categories.append(PREFIX_IN_OTHER_ISSUES)
                owner = amissue_owner.get(prefix)
                if owner and owner != issue.id:
                    categories.append(PREFIX_IS_OTHER_ISSUE_PID)
                other_exported_codes = (exported_codes.get(issue.id) or set()) - {prefix}
                if other_exported_codes:
                    categories.append(ISSUE_EXPORTED_WITH_OTHER_CODE)
                if issue.year and prefix[9:13] != issue.year:
                    categories.append(PREFIX_YEAR_DIFFERS)
        if prefix and issn_scielo and prefix[:9] != issn_scielo:
            categories.append(PREFIX_ISSN_DIFFERS)

        yield {
            "collection": collection.acron3,
            "journal_acron": scielo_journal.journal_acron,
            "issn_scielo": issn_scielo,
            "issue_id": issue and issue.id,
            "issue_year": issue and issue.year,
            "volume": issue and issue.volume,
            "number": issue and issue.number,
            "supplement": issue and issue.supplement,
            "issue_folder": issue and issue.issue_folder,
            "amissue_pids": "|".join(sorted(amissue_pids.get(issue and issue.id) or ())),
            "exported_issue_codes": "|".join(
                sorted(exported_codes.get(issue and issue.id) or ())
            ),
            "pid_v3": article.pid_v3,
            "pid_v2": article.pid_v2,
            "pid_v2_issue_pid": prefix,
            "categories": "|".join(categories),
        }
