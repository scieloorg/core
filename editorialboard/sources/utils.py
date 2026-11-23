import lxml.html
from lxml.etree import ParserError

EXSLT_NS = {"re": "http://exslt.org/regular-expressions"}


def parse_html(raw_html):
    """Documento lxml de raw_html, ou None se o HTML não puder ser lido."""
    try:
        return lxml.html.document_fromstring(raw_html)
    except ParserError:
        return None


def first_match(node, xpaths):
    """Primeiro nó encontrado pela primeira XPath de xpaths que casar."""
    for xpath in xpaths:
        found = node.xpath(f"({xpath})[1]", namespaces=EXSLT_NS)
        if found:
            return found[0]


def to_html(node):
    """HTML de node, ou None se ele não tiver texto."""
    if node is None or not node.text_content().strip():
        return None
    return lxml.html.tostring(node, encoding="unicode")
