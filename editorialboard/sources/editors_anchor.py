import lxml.html
from lxml.etree import ParserError

EXSLT_NS = {"re": "http://exslt.org/regular-expressions"}
# Página nova (/journal/.../about/#editors): a âncora e o que vem depois dela
EDITORS_ANCHOR_XPATH = (
    r'//*[re:test(@id, "^editors$", "i") or re:test(@name, "^editors$", "i")]'
)
EDITORS_END_XPATHS = (
    "following::*["
    r're:test(@id, "^(instructions|contact|about|policy)$", "i") or '
    r're:test(@name, "^(instructions|contact|about|policy)$", "i")]',
    'following::section[re:test(@class, "journalContacts")]',
    "following::footer",
)


def first_match(node, xpaths):
    """Primeiro nó encontrado pela primeira XPath de xpaths que casar."""
    for xpath in xpaths:
        found = node.xpath(f"({xpath})[1]", namespaces=EXSLT_NS)
        if found:
            return found[0]


def _section_end(marker):
    """Primeiro limite depois da âncora: a seção seguinte, o h1 dela ou o rodapé."""
    ends = []
    for xpath in EDITORS_END_XPATHS:
        found = marker.xpath(f"({xpath})[1]", namespaces=EXSLT_NS)
        if found:
            ends.append(found[0])
    headings = marker.xpath("following::h1")
    if marker.tag == "h1" and headings:
        ends.append(headings[0])
    elif len(headings) > 1:
        ends.append(headings[1])
    if not ends:
        return None
    return min(ends, key=lambda node: len(node.xpath("preceding::*")))


def extract_editors_anchor_section(raw_html):
    """
    Recorta o corpo editorial da página que tem a âncora #editors.

    A página traz várias seções (sobre, política, corpo editorial, instruções).
    O recorte começa depois do título da seção (o h1 "Corpo editorial") e
    para na seção seguinte ou no rodapé do site.
    Lista, parágrafos e marcadores permanecem como estão no HTML.
    Retorna o trecho ou None se não houver âncora ou conteúdo.
    """
    try:
        document = lxml.html.document_fromstring(raw_html)
    except ParserError:
        return None

    marker = first_match(document, (EDITORS_ANCHOR_XPATH,))
    if marker is None:
        return None

    footer = _section_end(marker)
    # A âncora costuma ser um <a> vazio dentro de um <p>. O h1 seguinte,
    # ou o próprio h1 quando ele tem id="editors", é o título da seção.
    if marker.tag == "a":
        start = marker.getparent() if marker.getparent() is not None else marker
        sibling = start.getnext()
    else:
        sibling = marker.getnext()
    skipped_title = marker.tag == "h1"

    fragment = lxml.html.Element("div")
    while sibling is not None:
        nxt = sibling.getnext()
        if footer is not None and (sibling is footer or footer in sibling.iter()):
            break
        if not skipped_title and sibling.tag == "h1":
            skipped_title = True
            sibling = nxt
            continue
        fragment.append(sibling)
        sibling = nxt

    if not fragment.text_content().strip():
        return None
    return lxml.html.tostring(fragment, encoding="unicode")
