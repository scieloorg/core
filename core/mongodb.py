from django.conf import settings

from pymongo import MongoClient


def get_client(uri=None):
    """
    Returns a MongoClient instance. 
    If no URI is provided, it uses the default MongoDB URI from settings.

    Args:
        uri (str): MongoDB URI. If None, uses the default from settings. Default value should be something like "mongodb://localhost:27017/".

    Returns:
        MongoClient: A MongoClient instance.
    """
    if not uri:
        uri = settings.MONGODB_URI

    try:
        client = MongoClient(uri)
        return client
    except Exception as e:
        raise Exception(f"Failed to connect to MongoDB: {str(e)}")


def write_to_db(data, database, collection, force_update=True, client=None):
    """
    Writes data to a MongoDB collection.
    If force_update is True, it replaces the document if it exists or inserts a new one.
    If force_update is False, it inserts a new document.
    If a client is not provided, it uses the default client from settings.

    Args:
        data (dict): Data to be written to the collection.
        database (str): Name of the MongoDB database.
        collection (str): Name of the MongoDB collection.
        force_update (bool): If True, replaces the document if it exists or inserts a new one. If False, inserts a new document.
        client (MongoClient): A MongoClient instance. If None, uses the default client from settings.

    Returns:
        bool: True if successful, False otherwise.

    Raises:
        Exception: If there is an error writing to the collection.
    """
    if not client:
        client = get_client()

    try:
        db = client[database]
        col = db[collection]
        if not force_update:
            col.insert_one(data)
        else:
            col.replace_one(
                {
                    "code": data["code"], 
                    "collection": data["collection"]
                },
                data,
                upsert=True
            )
        return True

    except Exception as e:
        raise Exception(f"Failed to write to MongoDB collection {col}: {str(e)}")
