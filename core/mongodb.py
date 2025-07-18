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
