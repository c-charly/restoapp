"""
Moteur de recommandation - Page d'accueil personnalisée.

Stratégie multi-signaux (fallback en cascade) :
  1. Utilisateur authentifié avec historique riche
     - Recommandations basées sur :
       - Tags des plats commandés / vus / mis au panier
       - Restaurants favoris
       - Plats les mieux notés dans les restaurants connus
       - Tendances de l'heure

  2. Utilisateur authentifié sans historique (nouveau)
     - Top plats globaux (notes + commandes)

  3. Utilisateur anonyme
     - Top plats globaux + trending Redis
"""
import logging
from datetime import timedelta
from collections import defaultdict

from django.utils import timezone
from django.db.models import Count, Avg, Q

logger = logging.getLogger("core.recommendations")

# Constantes
MAX_ITEMS = 20          # Nombre max d'items retournés
TRENDING_WINDOW_H = 3   # Fenêtre trending : 3 dernières heures
REDIS_TRENDING_KEY = "trending:items:{hour}"


# POINT D'ENTRÉE PRINCIPAL

def get_homepage_feed(user=None, lat: float = None, lng: float = None, limit: int = MAX_ITEMS) -> dict:
    """
    Construit le feed de la page d'accueil.

    Retourne :
    {
        "strategy": "personalized" | "trending" | "top_rated",
        "sections": [
            {
                "title": "Recommandés pour vous",
                "reason": "Basé sur vos commandes passées",
                "items": [ ... ]
            },
            ...
        ]
    }
    """
    sections = []
    strategy = "top_rated"

    if user and user.is_authenticated:
        user_profile = _get_user_signal_profile(user)

        if user_profile["has_history"]:
            strategy = "personalized"
            # Section 1 : Basé sur les goûts détectés
            taste_items = _items_by_taste_tags(user_profile, limit=limit // 2)
            if taste_items:
                sections.append({
                    "title": "Recommandés pour vous",
                    "reason": f"Basé sur vos {user_profile['total_orders']} commandes passées",
                    "items": taste_items,
                })

            # Section 2 : Restaurant favori - nouveautés
            fav_items = _items_from_favorite_restaurant(user_profile, limit=6)
            if fav_items:
                sections.append({
                    "title": f"Chez {user_profile['favorite_restaurant_name']}",
                    "reason": "Votre restaurant préféré",
                    "items": fav_items,
                })

            # Section 3 : Mieux notés dans vos restaurants connus
            top_rated_known = _top_rated_in_known_restaurants(user_profile, limit=6)
            if top_rated_known:
                sections.append({
                    "title": "Les mieux notés",
                    "reason": "Plats très appréciés dans vos restaurants",
                    "items": top_rated_known,
                })
        else:
            strategy = "trending"

    # Section Trending (toujours présente)
    trending = _get_trending_items(limit=8)
    if trending:
        sections.append({
            "title": "En ce moment",
            "reason": f"Plats populaires ces {TRENDING_WINDOW_H} dernières heures",
            "items": trending,
        })

    # Section Top global (fallback / complément)
    if len(sections) == 0 or strategy in ("trending", "top_rated"):
        top_global = _get_top_global_items(limit=limit)
        if top_global:
            sections.append({
                "title": "Les incontournables",
                "reason": "Plats les mieux notés sur la plateforme",
                "items": top_global,
            })

    return {
        "strategy": strategy,
        "user_authenticated": bool(user and user.is_authenticated),
        "sections": sections,
        "total_items": sum(len(s["items"]) for s in sections),
    }


# PROFIL DE GOÛTS UTILISATEUR

def _get_user_signal_profile(user) -> dict:
    """
    Extrait les signaux comportementaux de l'utilisateur.
    agrégations sur orders, item_ratings, analytics events.
    """
    from orders.models import Order, OrderItem
    from cart.models import ItemRating, CartItem
    from analytics.models import UserEvent

    profile = {
        "user_id": str(user.id),
        "has_history": False,
        "total_orders": 0,
        "favorite_restaurant_id": None,
        "favorite_restaurant_name": "",
        "known_restaurant_ids": [],
        "favorite_tags": [],          # tags les plus commandés
        "favorite_item_ids": [],      # items déjà commandés
        "high_rated_item_ids": [],    # items notés 4-5 étoiles
        "avoided_tags": [],           # tags des items annulés / mal notés
    }

    # Commandes passées
    orders_qs = Order.objects.filter(client=user, status="delivered").prefetch_related("items")
    total_orders = orders_qs.count()
    profile["total_orders"] = total_orders

    if total_orders == 0:
        return profile

    profile["has_history"] = True

    # Restaurant favori
    fav = (
        orders_qs.values("restaurant__id", "restaurant__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
        .first()
    )
    if fav:
        profile["favorite_restaurant_id"] = str(fav["restaurant__id"])
        profile["favorite_restaurant_name"] = fav["restaurant__name"] or ""

    # Restaurants connus
    profile["known_restaurant_ids"] = list(
        orders_qs.values_list("restaurant__id", flat=True).distinct()
    )[:10]
    profile["known_restaurant_ids"] = [str(r) for r in profile["known_restaurant_ids"]]

    # Tags et items depuis les snapshots PostgreSQL
    tag_counter = defaultdict(int)
    item_ids_ordered = []

    for order in orders_qs[:20]:  # Limiter pour perf
        for item in order.items.all():
            snap = item.snapshot_data or {}
            for tag in snap.get("tags", []):
                tag_counter[tag] += 1
            item_id = snap.get("id", "")
            if item_id:
                item_ids_ordered.append(item_id)

    profile["favorite_tags"] = [tag for tag, _ in sorted(tag_counter.items(), key=lambda x: -x[1])[:8]]
    profile["favorite_item_ids"] = list(set(item_ids_ordered))[:20]

    # Items bien notés (4-5 étoiles)
    profile["high_rated_item_ids"] = list(
        ItemRating.objects.filter(user=user, rating__gte=4)
        .values_list("item_id", flat=True)
        .distinct()[:20]
    )

    # Tags évités (items mal notés ou commandes annulées)
    bad_rated_items = list(
        ItemRating.objects.filter(user=user, rating__lte=2)
        .values_list("item_id", flat=True)
    )
    # (simplification : on ne charge pas les tags depuis MongoDB ici pour perf)

    # Items vus / ajoutés au panier sans commander (depuis analytics)
    viewed_item_ids = list(
        UserEvent.objects.filter(user=user, event_type="item_viewed")
        .values_list("object_id", flat=True)
        .distinct()[:30]
    )
    profile["viewed_item_ids"] = viewed_item_ids

    return profile


# STRATÉGIES DE RECOMMANDATION (MongoDB)

def _items_by_taste_tags(user_profile: dict, limit: int = 10) -> list:
    """
    récupère les items dont les tags correspondent aux goûts détectés.
    Exclut les items déjà commandés récemment (évite la redite).
    """
    from core.mongo import get_collection

    try:
        col = get_collection("menus")
        fav_tags = user_profile.get("favorite_tags", [])
        already_ordered = user_profile.get("favorite_item_ids", [])

        if not fav_tags:
            return []

        results = []
        pipeline = [
            {"$unwind": "$categories"},
            {"$unwind": "$categories.items"},
            {"$match": {
                "categories.items.available": True,
                "categories.items.tags": {"$in": fav_tags},
                "categories.items.id": {"$nin": already_ordered[:10]},  # Exclut récents
            }},
            {"$addFields": {
                # Score : nombre de tags en commun avec les favoris
                "match_score": {
                    "$size": {
                        "$ifNull": [
                            {"$setIntersection": ["$categories.items.tags", fav_tags]},
                            []
                        ]
                    }
                }
            }},
            {"$sort": {"match_score": -1, "categories.items.avg_rating": -1}},
            {"$limit": limit},
            {"$project": {
                "restaurant_id": 1,
                "item": "$categories.items",
                "match_score": 1,
                "_id": 0,
            }},
        ]

        docs = list(col.aggregate(pipeline))
        for doc in docs:
            item = doc["item"]
            item["restaurant_id"] = doc["restaurant_id"]
            item["match_score"] = doc.get("match_score", 0)
            item["recommendation_reason"] = f"Correspond à vos goûts ({', '.join(item.get('tags', [])[:2])})"
            results.append(_enrich_item(item))

        return results
    except Exception as e:
        logger.warning(f"_items_by_taste_tags failed: {e}")
        return []


def _items_from_favorite_restaurant(user_profile: dict, limit: int = 6) -> list:
    """
    plats du restaurant favori, triés par note, non encore commandés.
    """
    from core.mongo import get_collection

    try:
        fav_id = user_profile.get("favorite_restaurant_id")
        if not fav_id:
            return []

        col = get_collection("menus")
        already_ordered = user_profile.get("favorite_item_ids", [])

        pipeline = [
            {"$match": {"restaurant_id": fav_id}},
            {"$unwind": "$categories"},
            {"$unwind": "$categories.items"},
            {"$match": {
                "categories.items.available": True,
                "categories.items.id": {"$nin": already_ordered[:5]},
            }},
            {"$sort": {"categories.items.avg_rating": -1, "categories.items.total_ratings": -1}},
            {"$limit": limit},
            {"$project": {
                "restaurant_id": 1,
                "item": "$categories.items",
                "_id": 0,
            }},
        ]

        docs = list(col.aggregate(pipeline))
        results = []
        for doc in docs:
            item = doc["item"]
            item["restaurant_id"] = doc["restaurant_id"]
            item["recommendation_reason"] = "Votre restaurant favori"
            results.append(_enrich_item(item))
        return results
    except Exception as e:
        logger.warning(f"_items_from_favorite_restaurant failed: {e}")
        return []


def _top_rated_in_known_restaurants(user_profile: dict, limit: int = 6) -> list:
    """
    plats les mieux notés dans les restaurants connus de l'utilisateur.
    """
    from core.mongo import get_collection

    try:
        known_ids = user_profile.get("known_restaurant_ids", [])
        if not known_ids:
            return []

        col = get_collection("menus")
        pipeline = [
            {"$match": {"restaurant_id": {"$in": known_ids}}},
            {"$unwind": "$categories"},
            {"$unwind": "$categories.items"},
            {"$match": {
                "categories.items.available": True,
                "categories.items.avg_rating": {"$gte": 4},
                "categories.items.total_ratings": {"$gte": 1},
            }},
            {"$sort": {"categories.items.avg_rating": -1, "categories.items.total_ratings": -1}},
            {"$limit": limit},
            {"$project": {
                "restaurant_id": 1,
                "item": "$categories.items",
                "_id": 0,
            }},
        ]
        docs = list(col.aggregate(pipeline))
        results = []
        for doc in docs:
            item = doc["item"]
            item["restaurant_id"] = doc["restaurant_id"]
            item["recommendation_reason"] = f"Très apprécié - {item.get('avg_rating', 0):.1f}/5"
            results.append(_enrich_item(item))
        return results
    except Exception as e:
        logger.warning(f"_top_rated_in_known_restaurants failed: {e}")
        return []


def _get_trending_items(limit: int = 8) -> list:
    """
    items les plus vus/ajoutés au panier ces 3 dernières heures.
    Fallback sur top global si Redis vide.
    """
    from core.redis_client import get_redis
    from core.mongo import get_collection
    from datetime import datetime, timezone as tz

    try:
        r = get_redis()
        now = datetime.now(tz.utc)

        # Agréger les compteurs Redis des 3 dernières heures
        item_scores = defaultdict(int)
        for h in range(TRENDING_WINDOW_H):
            ts = now - timedelta(hours=h)
            # Compteur d'événements item_viewed par heure
            keys = r.keys(f"analytics:item_views:{ts.strftime('%Y%m%d%H')}:*")
            for key in keys[:50]:
                item_id = key.split(":")[-1]
                try:
                    count = int(r.get(key) or 0)
                    item_scores[item_id] += count
                except Exception:
                    pass

        if not item_scores:
            return _get_top_global_items(limit=limit)

        # Top item_ids par score
        top_item_ids = [
            item_id for item_id, _ in
            sorted(item_scores.items(), key=lambda x: -x[1])[:limit]
        ]

        # Récupérer les items depuis MongoDB
        col = get_collection("menus")
        pipeline = [
            {"$unwind": "$categories"},
            {"$unwind": "$categories.items"},
            {"$match": {
                "categories.items.id": {"$in": top_item_ids},
                "categories.items.available": True,
            }},
            {"$project": {
                "restaurant_id": 1,
                "item": "$categories.items",
                "_id": 0,
            }},
        ]
        docs = list(col.aggregate(pipeline))
        results = []
        for doc in docs:
            item = doc["item"]
            item["restaurant_id"] = doc["restaurant_id"]
            item["trending_score"] = item_scores.get(item.get("id", ""), 0)
            item["recommendation_reason"] = "Tendance du moment"
            results.append(_enrich_item(item))

        # Trier par trending_score
        results.sort(key=lambda x: x.get("trending_score", 0), reverse=True)
        return results[:limit]

    except Exception as e:
        logger.warning(f"_get_trending_items failed: {e}")
        return _get_top_global_items(limit=limit)


def _get_top_global_items(limit: int = 20) -> list:
    """
    top plats globaux triés par note moyenne puis nombre de ratings.
    Fallback universel.
    """
    from core.mongo import get_collection

    try:
        col = get_collection("menus")
        pipeline = [
            {"$unwind": "$categories"},
            {"$unwind": "$categories.items"},
            {"$match": {
                "categories.items.available": True,
            }},
            {"$sort": {
                "categories.items.avg_rating": -1,
                "categories.items.total_ratings": -1,
            }},
            {"$limit": limit},
            {"$project": {
                "restaurant_id": 1,
                "item": "$categories.items",
                "_id": 0,
            }},
        ]
        docs = list(col.aggregate(pipeline))
        results = []
        for doc in docs:
            item = doc["item"]
            item["restaurant_id"] = doc["restaurant_id"]
            item["recommendation_reason"] = "Plat populaire"
            results.append(_enrich_item(item))
        return results
    except Exception as e:
        logger.warning(f"_get_top_global_items failed: {e}")
        return []


# TRACKING VUES D'ITEMS (pour trending Redis)

def track_item_view(user_id: str, item_id: str, restaurant_id: str):
    """
    REDIS : incrémente le compteur de vues d'un item pour le calcul trending.
    TTL = 24h pour ne garder que les données récentes.
    """
    try:
        from core.redis_client import get_redis
        from datetime import datetime, timezone as tz
        r = get_redis()
        now = datetime.now(tz.utc)
        key = f"analytics:item_views:{now.strftime('%Y%m%d%H')}:{item_id}"
        r.incr(key)
        r.expire(key, 86400)  # TTL 24h
    except Exception as e:
        logger.debug(f"track_item_view failed: {e}")


# HELPER : enrichir un item avec les données restaurant PostgreSQL

def _enrich_item(item: dict) -> dict:
    """Ajoute les données restaurant (nom, note) et normalise l'item."""
    from restaurants.models import Restaurant
    from cart.models import RestaurantRating

    restaurant_id = item.get("restaurant_id", "")
    enriched = {
        "item_id": item.get("id", ""),
        "name": item.get("name", ""),
        "description": item.get("description", ""),
        "price": item.get("price", 0),
        "photos": item.get("photos", []),
        "tags": item.get("tags", []),
        "options": item.get("options", []),
        "calories": item.get("calories"),
        "allergenes": item.get("allergenes", []),
        "avg_rating": round(float(item.get("avg_rating") or 0), 2),
        "total_ratings": item.get("total_ratings", 0),
        "restaurant_id": restaurant_id,
        "restaurant_name": "",
        "restaurant_avg_rating": 0,
        "recommendation_reason": item.get("recommendation_reason", ""),
        "trending_score": item.get("trending_score"),
        "match_score": item.get("match_score"),
        "promo_price": item.get("promo_price"),
        "promo_ends_at": item.get("promo_ends_at"),
    }

    # Enrichir avec données PostgreSQL restaurant
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
        enriched["restaurant_name"] = restaurant.name
        enriched["restaurant_address"] = restaurant.address
        try:
            enriched["restaurant_avg_rating"] = float(restaurant.rating.avg_rating)
        except Exception:
            pass
    except Exception:
        pass

    return enriched
