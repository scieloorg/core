from config import celery_app

from book.sources.oai_books import harvest_books

@celery_app.task()
def load_books_from_oai_pmh(user_id, oai_pmh_book_uri):
    ##TODO
    ## get usuario da requisicao
    harvest_books(oai_pmh_book_uri, user_id)