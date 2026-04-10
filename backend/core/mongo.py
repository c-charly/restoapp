"""
Connexion MongoDB centralisée.
"""
import logging
from django.conf import settings
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

_client = None
_db = None


def get_mongo_client():
    """Retourne le client MongoDB (singleton)."""
    global _client
    if _client is None:
        try:
            _client = MongoClient(
                settings.DATABASES["nosql"]["CLIENT"]["host"],
                serverSelectionTimeoutMS=5000,
            )
            _client.admin.command("ping")
        except ConnectionFailure as e:
            logger.error(f"Connexion MongoDB échouée : {e}")
            raise
    return _client


def get_mongo_db():
    """Retourne la base MongoDB (singleton)."""
    global _db
    if _db is None:
        client = get_mongo_client()
        _db = client[settings.DATABASES["nosql"]["NAME"]]
    return _db


def get_collection(name: str):
    """Raccourci pour obtenir une collection MongoDB."""
    return get_mongo_db()[name]
