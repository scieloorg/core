"""
Periódicos presentes em mais de uma coleção, possivelmente com dados
diferentes (acrônimo e/ou PID) e, consequentemente, artigos com PIDs v2 e
XML diferentes em cada coleção.

Ex.: Psicologia USP
- scl: acron=pusp, pid=0103-6564, artigo S0103-65642009000300003
- psi: acron=psicousp, pid=1678-5177, artigo S1678-51772009000300003

No site novo, o acrônimo é a chave do periódico e o PID compõe o pid v2
(link legado), então os dados de cada coleção devem ser preservados.

Código que não é modelo de banco de dados; o registro por coleção está em
pid_provider.models.CollectionPidV2
"""

from django.apps import apps
from django.db.models import Q


def get_journal_pid_from_v2(pid_v2):
    """
    Retorna o PID do periódico (issn_scielo) contido no PID v2
    Ex.: S0103-65642009000300003 -> 0103-6564
    """
    if pid_v2 and len(pid_v2) == 23:
        return pid_v2[1:10]
    return None


def normalize_acron(acron):
    return acron and acron.strip().lower()


def get_xml_collections(xml_with_pre):
    """
    Retorna os dados do periódico em cada coleção em que está presente,
    identificado pelos ISSNs e pelo PID do periódico contido no pid v2,
    com a coleção principal primeiro

    Returns
    -------
    list of dict
        [{"collection": Collection, "journal_acron": str, "journal_pid": str,
          "is_main": bool}]

    Se o XML informa a coleção de origem (custom-meta), retorna somente
    os dados do periódico nesta coleção
    """

    issn_print = xml_with_pre.journal_issn_print
    issn_electronic = xml_with_pre.journal_issn_electronic
    pid_v2 = xml_with_pre.v2
    journal_acron = normalize_acron(xml_with_pre.journal_acron)
    journal_pid = get_journal_pid_from_v2(pid_v2)
    if not issn_print and not issn_electronic and not journal_pid:
        return []
    try:
        # Core
        model = apps.get_model("journal", "SciELOJournal")
        issn_path = "journal__official"
        acron_field = "journal_acron"
        pid_field = "issn_scielo"
    except LookupError:
        # Upload
        model = apps.get_model("proc", "JournalProc")
        issn_path = "journal__official_journal"
        acron_field = "acron"
        pid_field = "pid"

    q = Q()
    if issn_print:
        q |= Q(**{f"{issn_path}__issn_print": issn_print})
    if issn_electronic:
        q |= Q(**{f"{issn_path}__issn_electronic": issn_electronic})
    if journal_pid:
        q |= Q(**{pid_field: journal_pid})
    if journal_acron:
        q |= Q(**{acron_field: journal_acron})

    items = []
    main_item = None
    for item in model.objects.filter(q, collection__isnull=False).select_related(
        "collection"
    ):
        collection = item.collection
        is_main = collection.is_national_journal_collection
        data = {
            "is_main": is_main,
            "collection": collection,
            "journal_acron": getattr(item, acron_field),
            "journal_pid": getattr(item, pid_field),
        }
        if is_main:
            main_item = data
        else:
            items.append(data)
    if main_item:
        items.insert(0, main_item)

    return items