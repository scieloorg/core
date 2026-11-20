import logging

from curl_cffi import requests as curl_requests
from curl_cffi.requests.exceptions import ConnectionError, RequestException

from core.utils.bunny_shield import get as bunny_get
from editorialboard import choices
from editorialboard.sources.utils import first_match, parse_html, to_html

logger = logging.getLogger(__name__)

# https primeiro; http só quando o host não aceita conexão TLS
SCHEMES = ("https", "http")
# Fingerprint TLS/HTTP2 e headers do Chrome: o fingerprint do Python é bloqueado por WAFs
IMPERSONATE = "chrome"
HEADERS = {"Accept-Language": "es-ES,es;q=0.9,pt-BR;q=0.8,pt;q=0.7,en;q=0.6"}
TIMEOUT = (10, 30)
# Prefixo do arquivo {prefix}edboard.htm no site clássico
_EDBOARD_FILE_PREFIX = {"es": "e", "pt": "p", "en": "i"}

# Marcadores do cabeçalho (título, ISSN, logo), em ordem de prioridade
HEADER_XPATHS = (
    r'//body//*[re:test(@class, "^titulo$", "i")]',
    r'//body//text()[re:test(., "\bISSN\b", "i")]/..',
    r'//body//img[re:test(@src, "logo", "i")]',
)
# Marcadores do rodapé: bloco da navegação [Home] [Acerca...] / [Volver] ou <hr>
FOOTER_XPATHS = (
    r'a[re:test(@href, "(aboutj|instruc|subscrp)\.htm|history\.back", "i")]'
    r"/ancestor::*[self::p or self::center or self::div or self::td][1]",
    "hr",
)


def decode_html(content):
    # PostgreSQL rejects NUL in text and JSON. Classic pages sometimes embed
    # 0x00 (UTF-16 leftovers, padded exports); it is not part of the markup.
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("cp1252", errors="replace")
    return text.replace("\x00", "")


def request(session, address, schemes):
    """
    GET em address (sem protocolo), tentando cada protocolo de schemes
    enquanto a conexão falhar. Retorna (protocolo que conectou, resposta).
    """
    for scheme in schemes[:-1]:
        try:
            return scheme, bunny_get(session, f"{scheme}://{address}")
        except ConnectionError as e:
            logger.info(f"{scheme}://{address}: {e}")
    return schemes[-1], bunny_get(session, f"{schemes[-1]}://{address}")


def extract_edboard_section(raw_html):
    """
    Recorta da página edboard.htm só o trecho do corpo editorial, sem tratar
    o conteúdo: remove o cabeçalho e tudo antes dele, e a navegação/rodapé e
    tudo depois. A remoção segue a ordem do documento, então funciona mesmo
    quando o HTML malformado aninha a navegação dentro da tabela do corpo.
    Retorna o <body> recortado ou None se não sobrar conteúdo.
    """
    document = parse_html(raw_html)
    if document is None:
        return None

    marker = first_match(document, HEADER_XPATHS)
    if marker is None:
        header = None
        body = document.find("body")
        footer = first_match(document, (f"//{xpath}" for xpath in FOOTER_XPATHS))
    else:
        # Páginas com dois <html> concatenados: o conteúdo está no body do marcador
        header = (marker.xpath("ancestor-or-self::table[last()]") or [marker])[0]
        body = marker.xpath("ancestor::body")[0]
        footer = first_match(header, (f"following::{xpath}" for xpath in FOOTER_XPATHS))

    removed = []
    if footer is not None:
        removed += [footer, *footer.xpath("following::*")]
    if header is not None:
        removed += [*header.xpath("preceding::*"), header]
    for element in removed:
        parent = element.getparent()
        if parent is not None:
            parent.remove(element)

    return to_html(body)


def fetch_edboard_html(base_url, journal_acron):
    """
    Retorna uma lista com um resultado por idioma de
    EDBOARD_LANGUAGES_HTML_CLASSIC_WEBSITE: o HTML do corpo editorial
    ou a tentativa que falhou.
    """
    host = base_url.split("://")[-1].rstrip("/")
    schemes = SCHEMES
    results = []
    # curl_cffi mantém o cookie do Bunny Shield e o fingerprint que o requests de fetch_data não tem.
    with curl_requests.Session(
        impersonate=IMPERSONATE, headers=HEADERS, timeout=TIMEOUT, verify=False
    ) as session:
        for language, _label in choices.EDBOARD_LANGUAGES_HTML_CLASSIC_WEBSITE:
            address = f"{host}/revistas/{journal_acron}/{_EDBOARD_FILE_PREFIX[language]}edboard.htm"
            source_url = f"{schemes[0]}://{address}"
            http_status = None
            raw_html = None
            try:
                scheme, response = request(session, address, schemes)
                schemes = (scheme,)
                source_url = response.url
                http_status = response.status_code
                response.raise_for_status()
                text = decode_html(response.content)
                raw_html = text if text.strip() else None
            except RequestException as error:
                http_status = getattr(getattr(error, "response", None), "status_code", None)
            results.append(
                {
                    "language": language,
                    "source_url": source_url,
                    "http_status": http_status,
                    "raw_html": raw_html,
                }
            )
    return results
