"""
Client Redis centralisé.
REDIS : performance temps réel — point d'entrée unique pour cache, GeoSet, Pub/Sub
"""
import json
import logging
from django.conf import settings
import redis as redis_lib

logger = logging.getLogger(__name__)

_redis_client = None


def get_redis():
    """Retourne le client Redis (singleton)."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


# -----------------------------------------------------------------------
# Helpers Cache Menu
# -----------------------------------------------------------------------

MENU_CACHE_TTL = 600  # 10 minutes


def get_cached_menu(restaurant_id: str):
    """
    REDIS : évite un aller-retour MongoDB pour chaque lecture de menu.
    Retourne le menu désérialisé ou None si absent.
    """
    try:
        r = get_redis()
        data = r.get(f"menu:{restaurant_id}")
        return json.loads(data) if data else None
    except Exception as e:
        logger.warning(f"Redis get_cached_menu failed: {e}")
        return None


def set_cached_menu(restaurant_id: str, menu_data: dict):
    """
    REDIS : stocke le menu 10 min pour éviter les lectures MongoDB répétées.
    """
    try:
        r = get_redis()
        r.setex(f"menu:{restaurant_id}", MENU_CACHE_TTL, json.dumps(menu_data, default=str))
    except Exception as e:
        logger.warning(f"Redis set_cached_menu failed: {e}")


def invalidate_menu_cache(restaurant_id: str):
    """
    REDIS : invalide le cache après mise à jour du menu dans MongoDB.
    """
    try:
        r = get_redis()
        r.delete(f"menu:{restaurant_id}")
    except Exception as e:
        logger.warning(f"Redis invalidate_menu_cache failed: {e}")


# -----------------------------------------------------------------------
# Helpers Statut Commande
# -----------------------------------------------------------------------

ORDER_STATUS_TTL = 3600  # 1 heure


def set_order_status(order_id: str, status: str):
    """
    REDIS : cache le statut pour les WebSockets sans requête PostgreSQL.
    """
    try:
        r = get_redis()
        r.setex(f"order:{order_id}:status", ORDER_STATUS_TTL, status)
        r.publish(f"channel:order:{order_id}", json.dumps({"status": status}))
    except Exception as e:
        logger.warning(f"Redis set_order_status failed: {e}")

