"""
Panier live stocké dans Redis.
REDIS : le panier en cours de construction est en Redis
(TTL 2h), pas de requête PostgreSQL à chaque ajout/modif/suppression d'item.

Structure Redis :
  Clé   : cart:{user_id}
  Type  : String (JSON sérialisé)
  TTL   : 2 heures (renouvelé à chaque modification)

Structure JSON du panier Redis :
{
  "user_id": "uuid",
  "restaurant_id": "uuid",
  "restaurant_name": "Chez Mama Africa",
  "items": [
    {
      "item_id": "uuid-mongo",
      "item_name": "Poulet DG",
      "base_price": 3500,
      "quantity": 2,
      "selected_options": [{"label": "Extra sauce", "price": 200}],
      "options_extra_price": 200,
      "line_total": 7400,
      "special_instructions": "Pas trop épicé",
      "item_snapshot": { ... }   // copie complète de l'item MongoDB
    }
  ],
  "subtotal": 7400,
  "items_count": 2,
  "created_at": "ISO",
  "updated_at": "ISO"
}
"""
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from core.redis_client import get_redis

logger = logging.getLogger(__name__)

CART_TTL = 7200  # 2 heures
CART_KEY_PREFIX = "cart"


def _cart_key(user_id: str) -> str:
    return f"{CART_KEY_PREFIX}:{user_id}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_line_total(base_price: float, options_extra: float, qty: int) -> float:
    return round((base_price + options_extra) * qty, 2)


def _sum_options(options: list) -> float:
    return sum(float(o.get("price", 0)) for o in options)


def get_cart(user_id: str) -> dict | None:
    """
    Retourne le panier désérialisé ou None si inexistant/expiré.
    """
    try:
        r = get_redis()
        raw = r.get(_cart_key(user_id))
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Redis get_cart failed: {e}")
        return None


def set_cart(user_id: str, cart: dict) -> bool:
    """
    sauvegarde du panier avec renouvellement TTL.
    """
    try:
        cart["updated_at"] = _now_iso()
        r = get_redis()
        r.setex(_cart_key(user_id), CART_TTL, json.dumps(cart, default=str))
        return True
    except Exception as e:
        logger.warning(f"Redis set_cart failed: {e}")
        return False


def delete_cart(user_id: str) -> bool:
    """supprime le panier (après conversion ou abandon)."""
    try:
        r = get_redis()
        r.delete(_cart_key(user_id))
        return True
    except Exception as e:
        logger.warning(f"Redis delete_cart failed: {e}")
        return False


def init_cart(user_id: str, restaurant_id: str, restaurant_name: str) -> dict:
    """Crée un nouveau panier vide pour un restaurant donné."""
    cart = {
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "restaurant_name": restaurant_name,
        "items": [],
        "subtotal": 0.0,
        "items_count": 0,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    set_cart(user_id, cart)
    return cart


def add_item(
    user_id: str,
    item_snapshot: dict,
    quantity: int = 1,
    selected_options: list = None,
    special_instructions: str = "",
) -> dict:
    """
    Ajoute ou met à jour un item dans le panier Redis.
    Si le panier est vide ou pour un autre restaurant, lève une ValueError.
    """
    if selected_options is None:
        selected_options = []

    cart = get_cart(user_id)
    if not cart:
        raise ValueError("Panier inexistant. Initialisez le panier d'abord.")

    item_id = item_snapshot["id"]
    base_price = float(item_snapshot["price"])
    options_extra = _sum_options(selected_options)
    line_total = _compute_line_total(base_price, options_extra, quantity)

    # Chercher si l'item existe déjà
    existing_idx = next(
        (i for i, it in enumerate(cart["items"]) if it["item_id"] == item_id),
        None
    )

    item_entry = {
        "item_id": item_id,
        "item_name": item_snapshot["name"],
        "base_price": base_price,
        "quantity": quantity,
        "selected_options": selected_options,
        "options_extra_price": options_extra,
        "line_total": line_total,
        "special_instructions": special_instructions,
        "item_snapshot": item_snapshot,
    }

    if existing_idx is not None:
        # Mettre à jour l'existant (nouvelles options peuvent être différentes)
        cart["items"][existing_idx] = item_entry
    else:
        cart["items"].append(item_entry)

    _recalculate(cart)
    set_cart(user_id, cart)
    return cart


def update_item_quantity(user_id: str, item_id: str, quantity: int) -> dict:
    """Met à jour la quantité d'un item. quantity=0 - supprime l'item."""
    cart = get_cart(user_id)
    if not cart:
        raise ValueError("Panier inexistant.")

    if quantity <= 0:
        return remove_item(user_id, item_id)

    for item in cart["items"]:
        if item["item_id"] == item_id:
            item["quantity"] = quantity
            item["line_total"] = _compute_line_total(
                item["base_price"], item["options_extra_price"], quantity
            )
            break

    _recalculate(cart)
    set_cart(user_id, cart)
    return cart


def remove_item(user_id: str, item_id: str) -> dict:
    """Retire un item du panier."""
    cart = get_cart(user_id)
    if not cart:
        raise ValueError("Panier inexistant.")

    cart["items"] = [it for it in cart["items"] if it["item_id"] != item_id]
    _recalculate(cart)
    set_cart(user_id, cart)
    return cart


def clear_cart(user_id: str) -> dict:
    """Vide complètement le panier (garde le restaurant)."""
    cart = get_cart(user_id)
    if not cart:
        raise ValueError("Panier inexistant.")
    cart["items"] = []
    _recalculate(cart)
    set_cart(user_id, cart)
    return cart


def _recalculate(cart: dict):
    """Recalcule subtotal et items_count en place."""
    cart["subtotal"] = round(sum(it["line_total"] for it in cart["items"]), 2)
    cart["items_count"] = sum(it["quantity"] for it in cart["items"])
