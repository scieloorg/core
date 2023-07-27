from book.tasks import load_books_from_oai_pmh


def run(user_id=None, oai_pmh_book_uri=None):
    oai_pmh_book_uri = (
        oai_pmh_book_uri or "http://oai.books.scielo.org/oai-pmh"
    )
    load_books_from_oai_pmh.apply_async(args=(user_id, oai_pmh_book_uri))