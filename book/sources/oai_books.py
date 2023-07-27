import logging
import re
from datetime import datetime
from urllib.parse import urlparse
from sickle import Sickle

from lxml import etree

from book.models import Book, Institution, RecRaw
from book.utils.utils import parse_author_name
from core.models import Language
from researcher.models import Researcher

namespaces = {
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class BooksOaiPmhSaveError(Exception):
    def __init__(self, message):
        super().__init__(f"Failed to save book data from OAI-PMH: {message}")


def harvest_books(oai_pmh_book_uri, user_id):
    URL = oai_pmh_book_uri

    sickle = Sickle(URL)
    recs = sickle.ListRecords(metadataPrefix="oai_dc")
    books = []
    for rec in recs:
        if not rec.header.deleted:
            book = get_book(rec)
            create_or_update_book(book, user_id)


def get_book(rec):
    """
    {
        'title': 'foo',
        'creator': ['foo', 'foo'] or 'creator': 'foo',
        'description': 'foo',
        'publisher': 'foo',
        'date': '2016',
        'type': 'book',
        'format': ['pdf', 'epub'],
        'identifier': 'http://books.scielo.org/id/ffd4c',
        'language': 'pt'
    }
    """
    root = etree.fromstring(str(rec))
    book_dict = {}
    nodes = [
        "title",
        "creator",
        "description",
        "publisher",
        "date",
        # "type",
        # "format",
        "identifier",
        "language",
    ]
    for node in nodes:
        book_dict[node] = []
        for r in root.xpath(f".//dc:{node}", namespaces=namespaces):
            if len(root.xpath(f".//dc:{node}", namespaces=namespaces)) > 1:
                book_dict[node].append(r.text)
            else:
                book_dict.update({node: r.text})
    book_dict.update({"rec": rec.raw})
    return book_dict


def create_or_update_book(book, user=None):
    researchers = get_or_create_researchers(book.get("creator"))
    language = Language.get_or_create(code2=book.get("language"))
    institution = Institution.get_or_create(
        inst_name=book.get("publisher"),
        inst_acronym=None,
        level_1=None,
        level_2=None,
        level_3=None,
        location=None,
        official=None,
        is_official=None,
        user=user,
    )
    try:
        obj = Book.create_or_update(
            title=book.get("title"),
            synopsis=book.get("description"),
            year=book.get("date"),
            identifier=book.get("identifier"),
            researchers=researchers,
            institution=institution,
            language=language,
            user=user,
            doi=None,
            isbn=None,
            eisbn=None,
            location=None,
        )
    except Exception as e:
        # TODO cria um registro das falhas de modo que fiquem
        # acessíveis na área administrativa
        # para que o usuário fique sabendo quais itens falharam
        raise BooksOaiPmhSaveError(e)

    RecRaw.objects.get_or_create(
        rec=book.get("rec"),
        book=obj,
        creator=user,
    )


def get_or_create_researchers(researchers):
    data = []
    if isinstance(researchers, str):
        researchers = [researchers]

    for researcher in researchers:
        researcher = parse_author_name(researcher)
        obj = Researcher.get_or_create(
            given_names=researcher.get("given_names"),
            last_name=researcher.get("surname"),
            suffix=None,
            orcid=None,
            lattes=None,
            email=None,
            institution_name=None,
        )
        data.append(obj)
    return data
