from core.utils import utils
from issue.utils.correspondencia import correspondencia_issue
## TODO
## Mover rename_dictionary_keys para core.utils
from journal.utils.rename_dictionary_keys import rename_dictionary_keys
from issue.utils.issue_utils import get_or_create_issue


def process_issue_article_meta(user):
    offset = 0
    collection = "scl"
    issue_dict = {}
    data = request_issue_article_meta(collection=collection, limit=100)
    total_limit = data["meta"]["total"]
    while offset < total_limit :
        for issue in data["objects"]:
            code = issue["code"]
            url_issue = f"https://articlemeta.scielo.org/api/v1/issue/?code={code}"
            data_issue = utils.fetch_data(
                url_issue, json=True, timeout=30, verify=True
            )
            issue_dict = rename_dictionary_keys(
                data_issue["issue"], correspondencia_issue
            )
            get_or_create_issue(
                issn_scielo=issue_dict.get("scielo_issn"),
                volume=issue_dict.get("volume"),
                number=issue_dict.get("number"),
                supplement_volume=issue_dict.get("suplement_volume"),
                supplement_number=issue_dict.get("suplement_number"),
                data_iso=issue_dict.get("date_iso"),
                sections_data=issue_dict.get("sections_data"),
                user=user,
            )
        offset+=100
        data = request_issue_article_meta(collection=collection, limit=100, offset=offset)



def request_issue_article_meta(collection="scl", limit=10, offset=None, ):
    offset = f"&offset={offset}" if offset else ""
    url = (
        f"https://articlemeta.scielo.org/api/v1/issue/identifiers/?collection={collection}&limit={limit}"
        + offset
    )
    data = utils.fetch_data(url, json=True, timeout=30, verify=True)
    return data