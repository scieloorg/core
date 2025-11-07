from datetime import datetime, timezone
import logging

from django.conf import settings
from pymongo import MongoClient


MONGODB_DATABASE = settings.MONGODB_DATABASE
MONGODB_URI = settings.MONGODB_URI


def get_client(uri=None):
    """
    Returns a MongoClient instance.
    If no URI is provided, it uses the default MongoDB URI from settings.

    Args:
        uri (str): MongoDB URI. If None, uses the default from settings. Default value should be something like "mongodb://localhost:27017/".

    Returns:
        MongoClient: A MongoClient instance.
    """
    try:
        uri = uri or MONGODB_URI
        return MongoClient(uri)
    except Exception as e:
        raise Exception(f"Failed to connect to MongoDB {uri}: {str(e)}")


def get_mongodb_collection(mongodb_collection_name):
    try:
        return get_client()[MONGODB_DATABASE][mongodb_collection_name]
    except Exception as e:
        raise Exception(
            f"Failed to connect to MongoDB collection: {mongodb_collection_name}: {str(e)}"
        )


def write_item(mongodb_collection_name, data, filter_query=None):
    try:
        mongodb_collection = get_mongodb_collection(mongodb_collection_name)
        # collection = scielo collection
        filter_query = filter_query or {
            "code": data["code"],
            "collection": data["collection"],
        }
        convert_dates(data)
        # A atualização define os campos, incluindo a última visita
        update_data = {
            "$set": data,
        }
        result = mongodb_collection.update_one(filter_query, update_data, upsert=True)
        # O objeto UpdateResult contém:
        # result.matched_count      # Número de documentos que corresponderam ao filtro
        # result.modified_count      # Número de documentos que foram modificados
        # result.upserted_id        # O _id do documento inserido (se houve upsert), None caso contrário
        # result.acknowledged       # True se a operação foi reconhecida pelo servidor
        # result.raw_result         # Dicionário com a resposta completa do servidor
        # Verificando o resultado
        response = {}
        response["filter_query"] = filter_query
        response["result"] = result.raw_result
        response["upserted_id"] = result.upserted_id
        response["success"] = bool(
            result.upserted_id or result.modified_count or result.acknowledged
        )
        return response
    except Exception as e:
        logging.exception(f"unable to create/update {filter_query} ({MONGODB_DATABASE} {MONGODB_URI}) {str(e)}")
        raise Exception(f"Unable to create/update {filter_query} {MONGODB_DATABASE}: {str(e)}")


def fix_document_processing_date(document):
    if "processing_date" in document:
        document["processing_date"] = datetime_fromisoformat(document["processing_date"])
    if "created_at" in document:
        document["created_at"] = datetime_fromisoformat(document["created_at"])
    else:
        document["created_at"] = datetime.now(timezone.utc)


def datetime_fromisoformat(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        logging.warning(f"Invalid date format: {date_str}. Setting to current UTC time.")
        return datetime.now(timezone.utc)


def convert_dates(data):
    fix_document_processing_date(data)
    for key in ["title", "issue", "article"]:
        try:
            fix_document_processing_date(data[key])
        except KeyError:
            return

