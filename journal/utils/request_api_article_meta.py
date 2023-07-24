from core.utils import utils


def request_journal_article_meta(offset=None, limit=10, collection="scl"):
    offset = f"&offset={offset}" if offset else ""
    url = (
        f"https://articlemeta.scielo.org/api/v1/journal/identifiers/?collection={collection}&limit={limit}"
        + offset
    )
    data = utils.fetch_data(url, json=True, timeout=30, verify=True)
    return data
