import requests
import xmltodict
import json

from .models import ScieloJournal, Issue
from processing_errors.models import ProcessingError


def get_collection():
    try:
        collections_urls = requests.get("https://articlemeta.scielo.org/api/v1/collection/identifiers/",
                                        timeout=10)
        for collection in json.loads(collections_urls.text):
            yield collection.get('domain')

    except Exception as e:
        error = ProcessingError()
        error.step = "Collection url search error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


def get_issn(collection):
    try:
        collections = requests.get(
            f"http://{collection}/scielo.php?script=sci_alphabetic&lng=es&nrm=iso&debug=xml", timeout=10)
        data = xmltodict.parse(collections.text)

        for issn in data['SERIALLIST']['LIST']['SERIAL']:
            try:
                yield issn['TITLE']['@ISSN']
            except Exception as e:
                error = ProcessingError()
                error.item = f"ISSN's list of {collection} collection error"
                error.step = "Get an ISSN from a collection error"
                error.description = str(e)[:509]
                error.type = str(type(e))
                error.save()

    except Exception as e:
        error = ProcessingError()
        error.step = "Collection ISSN's list search error"
        error.description = str(e)[:509]
        error.type = str(type(e))
        error.save()


