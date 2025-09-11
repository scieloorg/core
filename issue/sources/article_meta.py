import logging

from core.utils import utils
from core.utils.rename_dictionary_keys import rename_issue_dictionary_keys
from issue.utils.correspondencia import correspondencia_issue
from issue.utils.issue_utils import get_or_create_issue
from collection.models import Collection

def process_issue_article_meta(collection, limit, user):
    offset = 0
    for collection_acron3 in list_of_collections_acron3(collection):
        data = request_issue_article_meta(collection=collection_acron3, limit=limit)
        total_limit = data["meta"]["total"]
        while offset < total_limit:
            for issue in data["objects"]:
                code = issue["code"]
                url_issue = f"https://articlemeta.scielo.org/api/v1/issue/?code={code}"
                data_issue = utils.fetch_data(url_issue, json=True, timeout=30, verify=True)
                issue_dict = rename_issue_dictionary_keys(
                    [data_issue["issue"]], correspondencia_issue
                )
                try:
                    get_or_create_issue(
                        issn_scielo=issue_dict.get("scielo_issn"),
                        volume=issue_dict.get("volume"),
                        number=issue_dict.get("number"),
                        supplement_volume=issue_dict.get("supplement_volume"),
                        supplement_number=issue_dict.get("supplement_number"),
                        data_iso=issue_dict.get("date_iso"),
                        sections_data=issue_dict.get("sections_data"),
                        markup_done=issue_dict.get("markup_done"),
                        user=user,
                    )
                except Exception as exc:
                    logging.exception(f"Error ao criar isssue com code: {code}. Exception: {exc}")
            offset += 100
            data = request_issue_article_meta(
                collection=collection, limit=limit, offset=offset
            )


def list_of_collections_acron3(collections):
    query_collection = Collection.objects
    if not collections:
        collections = query_collection.all().values_list("acron3", flat=True)
    elif collections:
        if isinstance(collections, list):
            collections = [collections]
        collections = query_collection.filter(acron3__in=collections).values_list("acron3", flat=True)    
    return [collection for collection in collections]


def request_issue_article_meta(
    collection="scl",
    limit=10,
    offset=None,
):
    if not limit:
        limit = 10
    offset = f"&offset={offset}" if offset else ""
    url = (
        f"https://articlemeta.scielo.org/api/v1/issue/identifiers/?collection={collection}&limit={limit}"
        + offset
    )
    data = utils.fetch_data(url, json=True, timeout=30, verify=True)
    return data
