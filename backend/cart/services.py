"""
Logique métier du panier et du checkout.

Flux checkout (conversion panier - commande) :
  1. Récupérer le panier depuis Redis
  2. Vérifier disponibilité des items dans MongoDB
  3. Recalculer le total
  4. BEGIN TRANSACTION PostgreSQL
      a. Débiter le wallet
      b. Créer Order + OrderItems avec snapshot complet (options incluses)
      c. Créer WalletTransaction
      d. Marquer CartSession comme "converted"
  5. COMMIT / ROLLBACK
  6. Post-transaction : supprimer panier Redis + Redis Pub/Sub + MongoDB log
"""
import logging
from decimal import Decimal
from datetime import datetime, timezone

from django.db import transaction
from django.utils import timezone as dj_timezone

from accounts.models import Wallet
from restaurants.models import Restaurant
from orders.models import Order, OrderItem, WalletTransaction
from core.mongo import get_collection
from core.redis_client import set_order_status
from core.activity_log import log_activity
from .models import CartSession, CartItem
from .redis_cart import (
    get_cart, set_cart, delete_cart, init_cart,
    add_item as redis_add_item,
    update_item_quantity as redis_update_qty,
    remove_item as redis_remove_item,
    clear_cart as redis_clear,
)

logger = logging.getLogger(__name__)


class CartError(Exception):
    pass


class InsufficientFundsError(CartError):
    pass


class RestaurantMismatchError(CartError):
    pass


class EmptyCartError(CartError):
    pass


def _find_item_in_menu(menu_doc: dict, item_id: str) -> dict | None:
    for category in menu_doc.get("categories", []):
        for item in category.get("items", []):
            if str(item.get("id", "")) == item_id:
                return item
    return None


# OPÉRATIONS PANIER (Redis live + PostgreSQL historique)

def get_or_create_cart(user, restaurant_id: str) -> dict:
    """
    Récupère le panier Redis actif ou en crée un nouveau.
    Si l'utilisateur avait un panier pour un autre restaurant - erreur.
    REDIS : performance temps réel - lecture/écriture panier <1ms.
    """
    from restaurants.models import Restaurant as R
    restaurant = R.objects.get(id=restaurant_id)

    existing = get_cart(str(user.id))
    if existing:
        if existing["restaurant_id"] != restaurant_id:
            raise RestaurantMismatchError(
                f"Panier déjà ouvert pour '{existing['restaurant_name']}'. "
                f"Videz-le avant d'en ouvrir un nouveau."
            )
        return existing

    # Créer session PostgreSQL pour tracking
    CartSession.objects.filter(user=user, status="active").update(
        status="abandoned",
        abandoned_at=dj_timezone.now(),
    )
    session = CartSession.objects.create(
        user=user,
        restaurant=restaurant,
        redis_key=f"cart:{user.id}",
    )

    cart = init_cart(str(user.id), restaurant_id, restaurant.name)
    cart["cart_session_id"] = str(session.id)
    set_cart(str(user.id), cart)

    # Tracker événement analytique
    _track_cart_event(user, "cart_opened", restaurant_id, restaurant.name)
    return cart


def add_item_to_cart(
    user,
    restaurant_id: str,
    item_id: str,
    quantity: int,
    selected_options: list,
    special_instructions: str,
) -> dict:
    """
    Ajoute un item au panier Redis + met à jour PostgreSQL CartSession.
    Récupère l'item depuis MongoDB pour validation et snapshot.
    """
    # 1. Valider que le panier existe pour ce restaurant
    cart = get_or_create_cart(user, restaurant_id)

    # 2. Récupérer l'item depuis MongoDB pour validation et snapshot
    col = get_collection("menus")
    menu_doc = col.find_one({"restaurant_id": restaurant_id})
    if not menu_doc:
        raise CartError("Menu introuvable pour ce restaurant.")

    item_doc = _find_item_in_menu(menu_doc, item_id)
    if not item_doc:
        raise CartError(f"Plat '{item_id}' introuvable dans le menu.")
    if not item_doc.get("available", True):
        raise CartError(f"Le plat '{item_doc['name']}' n'est pas disponible actuellement.")

    # 3. Valider les options choisies vs options disponibles
    available_options = {o["label"]: o["price"] for o in item_doc.get("options", [])}
    for opt in selected_options:
        if opt["label"] not in available_options:
            raise CartError(f"Option '{opt['label']}' non disponible pour ce plat.")
        opt["price"] = available_options[opt["label"]]  # Prix officiel, pas celui du client

    # 4. Construire snapshot complet (inclut image, tags, options, note)
    item_snapshot = {
        "id": item_id,
        "name": item_doc["name"],
        "price": item_doc["price"],
        "description": item_doc.get("description", ""),
        "photos": item_doc.get("photos", []),
        "tags": item_doc.get("tags", []),
        "options": item_doc.get("options", []),
        "calories": item_doc.get("calories"),
        "allergenes": item_doc.get("allergenes", []),
        "avg_rating": item_doc.get("avg_rating", None),
        "total_ratings": item_doc.get("total_ratings", 0),
    }

    # 5. Ajouter dans Redis
    updated_cart = redis_add_item(
        user_id=str(user.id),
        item_snapshot=item_snapshot,
        quantity=quantity,
        selected_options=selected_options,
        special_instructions=special_instructions,
    )

    # 6. Mettre à jour PostgreSQL CartSession (subtotal + items_count)
    _sync_cart_session_to_pg(user, updated_cart)

    # 7. Tracker analytique
    _track_cart_event(
        user, "item_added_to_cart", restaurant_id,
        menu_doc.get("restaurant_name", ""),
        item_id=item_id, item_name=item_doc["name"],
        price=item_doc["price"], options=selected_options,
    )

    return updated_cart


def update_cart_item(user, item_id: str, quantity: int) -> dict:
    """Met à jour la quantité d'un item dans le panier."""
    cart = get_cart(str(user.id))
    if not cart:
        raise CartError("Aucun panier actif.")

    event = "item_removed_from_cart" if quantity == 0 else "item_quantity_updated"
    updated = redis_update_qty(str(user.id), item_id, quantity)
    _sync_cart_session_to_pg(user, updated)

    _track_cart_event(
        user, event, cart["restaurant_id"], cart["restaurant_name"],
        item_id=item_id, quantity=quantity,
    )
    return updated


def clear_user_cart(user) -> dict:
    """Vide le panier de l'utilisateur."""
    cart = get_cart(str(user.id))
    if not cart:
        raise CartError("Aucun panier actif.")
    updated = redis_clear(str(user.id))
    _sync_cart_session_to_pg(user, updated)
    _track_cart_event(user, "cart_cleared", cart["restaurant_id"], cart["restaurant_name"])
    return updated


# CHECKOUT - Conversion panier -> commande atomique

def checkout(user, delivery_address: str = "") -> Order:
    """
    Convertit le panier Redis en commande PostgreSQL (transaction atomique).

    Flux complet :
    1. Lecture panier Redis
    2. Revalidation prix depuis MongoDB (sécurité)
    3. Vérification solde wallet (PostgreSQL)
    4. BEGIN TRANSACTION
       a. Débit wallet
       b. Création Order
       c. Création OrderItems avec snapshot complet (options incluses)
       d. WalletTransaction
       e. CartSession - "converted"
    5. COMMIT / ROLLBACK
    6. Post-transaction : delete panier Redis + Pub/Sub + MongoDB log
    """
    # 1. Récupérer le panier Redis
    cart = get_cart(str(user.id))
    if not cart:
        raise EmptyCartError("Aucun panier actif.")
    if not cart["items"]:
        raise EmptyCartError("Le panier est vide.")

    restaurant_id = cart["restaurant_id"]

    # 2. Revalider depuis MongoDB (prix de référence)
    col = get_collection("menus")
    menu_doc = col.find_one({"restaurant_id": restaurant_id})
    if not menu_doc:
        raise CartError("Menu introuvable. Impossible de valider la commande.")

    # Recomputer le total
    order_items_data = []
    total = Decimal("0")

    for cart_item in cart["items"]:
        item_doc = _find_item_in_menu(menu_doc, cart_item["item_id"])
        if not item_doc:
            raise CartError(f"Plat '{cart_item['item_name']}' n'est plus disponible.")

        base_price = Decimal(str(item_doc["price"]))
        options_extra = sum(
            Decimal(str(opt.get("price", 0)))
            for opt in cart_item.get("selected_options", [])
        )
        unit_price = base_price + options_extra
        qty = cart_item["quantity"]
        line_total = unit_price * qty
        total += line_total

        order_items_data.append({
            "item_name": item_doc["name"],
            "item_price": unit_price,
            "quantity": qty,
            # snapshot complet avec options choisies - données analytiques précieuses
            "snapshot_data": {
                "id": cart_item["item_id"],
                "name": item_doc["name"],
                "base_price": float(base_price),
                "options_extra_price": float(options_extra),
                "unit_price": float(unit_price),
                "line_total": float(line_total),
                "selected_options": cart_item.get("selected_options", []),
                "special_instructions": cart_item.get("special_instructions", ""),
                "tags": item_doc.get("tags", []),
                "photos": item_doc.get("photos", []),
                "calories": item_doc.get("calories"),
            },
        })

    with transaction.atomic():
        # 3. Vérifier solde
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
            wallet = Wallet.objects.select_for_update().get(user=user)
        except Restaurant.DoesNotExist:
            raise CartError("Restaurant introuvable.")

        if wallet.balance < total:
            raise InsufficientFundsError(
                f"Solde insuffisant : {wallet.balance} disponible, {total} requis."
            )

        # 4. Transaction atomique PostgreSQL
        # 4a. Débit wallet
        wallet.balance -= total
        wallet.save(update_fields=["balance"])

        # 4b. Création commande
        order = Order.objects.create(
            client=user,
            restaurant=restaurant,
            status="pending",
            total_price=total,
            delivery_address=delivery_address,
        )

        # 4c. Création OrderItems (snapshot inclut options, instructions, photos)
        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)

        # 4d. Transaction financière
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=total,
            type="debit",
            order=order,
            description=f"Commande #{order.id} - {restaurant.name}",
        )

        # 4e. Marquer CartSession PostgreSQL comme convertie
        CartSession.objects.filter(user=user, status="active").update(
            status="converted",
            order_id=order.id,
            subtotal=total,
        )

        # Sauvegarder CartItems PostgreSQL pour analyse comportementale
        session = CartSession.objects.filter(user=user, status="converted").order_by("-updated_at").first()
        if session:
            for cart_item in cart["items"]:
                CartItem.objects.create(
                    cart=session,
                    item_id=cart_item["item_id"],
                    item_name=cart_item["item_name"],
                    base_price=Decimal(str(cart_item["base_price"])),
                    quantity=cart_item["quantity"],
                    selected_options=cart_item.get("selected_options", []),
                    options_extra_price=Decimal(str(cart_item.get("options_extra_price", 0))),
                    special_instructions=cart_item.get("special_instructions", ""),
                    item_snapshot=cart_item.get("item_snapshot", {}),
                )

    # 5. Post-transaction
    delete_cart(str(user.id))
    set_order_status(str(order.id), "pending")

    log_activity(
        str(user.id),
        "order_created_from_cart",
        {
            "order_id": str(order.id),
            "restaurant": restaurant.name,
            "total": str(total),
            "items_count": len(order_items_data),
            "items": [
                {
                    "name": d["item_name"],
                    "qty": d["quantity"],
                    "options": d["snapshot_data"].get("selected_options", []),
                }
                for d in order_items_data
            ],
        },
    )

    _track_cart_event(
        user, "order_confirmed", restaurant_id, restaurant.name,
        order_id=str(order.id), total=float(total),
    )

    return order


# HELPERS INTERNES

def _sync_cart_session_to_pg(user, cart: dict):
    """Met à jour CartSession PostgreSQL avec les stats du panier Redis."""
    try:
        CartSession.objects.filter(user=user, status="active").update(
            subtotal=Decimal(str(cart.get("subtotal", 0))),
            items_count=cart.get("items_count", 0),
        )
    except Exception as e:
        logger.warning(f"_sync_cart_session_to_pg failed: {e}")


def _track_cart_event(user, event_type: str, restaurant_id: str, restaurant_name: str, **kwargs):
    """Log analytique d'un événement panier."""
    try:
        from analytics.models import UserEvent
        UserEvent.objects.create(
            user=user,
            event_type=event_type if event_type in dict(UserEvent.EVENT_TYPES) else "item_added_to_cart",
            object_type="cart",
            object_id=restaurant_id,
            properties={
                "restaurant_id": restaurant_id,
                "restaurant_name": restaurant_name,
                **kwargs,
            },
        )
    except Exception as e:
        logger.debug(f"_track_cart_event failed: {e}")
