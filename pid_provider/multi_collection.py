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

from pid_provider.exceptions import (
    MultipleCollectionsMatchedErrorToGetPidProviderXMLError,
)


def get_journal_pid_from_v2(pid_v2):
    """
    Retorna o PID do periódico (issn_scielo) contido no PID v2
    Ex.: S0103-65642009000300003 -> 0103-6564
    """
    if pid_v2 and len(pid_v2) == 23:
        return pid_v2[1:10]
    return None


def get_xml_categorized_collections(xml_with_pre):
    """
    Retorna os dados do periódico em cada coleção em que está presente,
    identificado pelo PID do periódico contido no pid v2 ou pelo acrônimo

    Returns
    -------
    dict
        items: [{"collection": Collection, "collection_acron": str,
                 "journal_acron": str, "journal_pid": str}]
            todas as coleções do periódico
        matched_items: items cujos PID e acrônimo do periódico são os do XML
    """
    result = {"items": [], "matched_items": []}

    journal_pid = get_journal_pid_from_v2(xml_with_pre.v2)
    journal_acron = xml_with_pre.journal_acron
    if not journal_pid and not journal_acron:
        # Q() vazio retornaria todos os periódicos
        return result
    try:
        # Core
        model = apps.get_model("journal", "SciELOJournal")
        acron_field = "journal_acron"
        pid_field = "issn_scielo"
    except LookupError:
        # Upload
        model = apps.get_model("proc", "JournalProc")
        acron_field = "acron"
        pid_field = "pid"

    q = Q()
    if journal_pid:
        q |= Q(**{pid_field: journal_pid})
    if journal_acron:
        q |= Q(**{acron_field: journal_acron})

    for item in model.objects.filter(q, collection__isnull=False).select_related(
        "collection"
    ):
        collection = item.collection
        j_acron = getattr(item, acron_field)
        j_pid = getattr(item, pid_field)
        data = {
            "collection": collection,
            "collection_acron": get_collection_acron(collection),
            "journal_acron": j_acron,
            "journal_pid": j_pid,
        }
        result["items"].append(data)
        # match: mesmos PID e acrônimo do periódico do XML (ambos exigidos)
        if (
            journal_pid
            and journal_acron
            and j_pid == journal_pid
            and j_acron == journal_acron
        ):
            result["matched_items"].append(data)
    return result


def get_xml_collection_acron(xml_with_pre):
    """
    Identifica a coleção de origem do XML que não a informa (custom-meta):
    a coleção cujos PID (contido no pid v2) e acrônimo do periódico são os
    do XML

    - nenhuma coleção com match: None (register levanta
      RequiredCollectionErrorToGetPidProviderXMLError)
    - uma coleção com match: esta
    - mais de uma, sendo ou não a nacional: ambíguo, levanta
      MultipleCollectionsMatchedErrorToGetPidProviderXMLError
    """
    if xml_with_pre.collection:
        return xml_with_pre.collection
    matched_items = get_xml_categorized_collections(xml_with_pre)["matched_items"]
    if len(matched_items) > 1:
        raise MultipleCollectionsMatchedErrorToGetPidProviderXMLError(
            f"Unable to identify the XML collection: journal "
            f"{get_journal_pid_from_v2(xml_with_pre.v2)} "
            f"{xml_with_pre.journal_acron} found in "
            f"{[item['collection_acron'] for item in matched_items]}. "
            "Please provide collection_acron"
        )
    if matched_items:
        return matched_items[0]["collection_acron"]
    return None


def get_collection_acron(collection):
    """
    Acrônimo da coleção: Collection.acron3 (Core) ou Collection.acron (Upload)
    """
    return getattr(collection, "acron3", None) or getattr(collection, "acron", None)
