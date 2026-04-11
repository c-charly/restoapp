"""
Service de création de commande

MONGODB : lecture du menu pour récupérer prix et snapshots
REDIS : performance temps réel — publication du statut initial après transaction
"""
import logging
from decimal import Decimal
from django.db import transaction

from accounts.models import Wallet
from restaurants.models import Restaurant
from core.mongo import get_collection
from core.redis_client import set_order_status
from core.activity_log import log_activity
from .models import Order, OrderItem, WalletTransaction

logger = logging.getLogger(__name__)


class InsufficientFundsError(Exception):
    pass


class ItemNotFoundError(Exception):
    pass


class MenuNotFoundError(Exception):
    pass


def _find_item_in_menu(menu_doc: dict, item_id: str):
    """Cherche un item dans les catégories du menu MongoDB."""
    for category in menu_doc.get("categories", []):
        for item in category.get("items", []):
            if str(item.get("id", "")) == item_id:
                return item
    return None


def create_order(user, restaurant_id: str, items_requested: list, delivery_address: str = "") -> Order:
    """
    Flux :
    1. Lire les items depuis MongoDB (menu)
    2. Calculer le total
    3. Vérifier solde Wallet (PostgreSQL)
    4. BEGIN TRANSACTION PostgreSQL
       a. Débiter le Wallet - créer WalletTransaction
       b. Créer l'Order
       c. Créer les OrderItems avec snapshot_data (copie figée du menu MongoDB)
    5. COMMIT (ou ROLLBACK si erreur)
    6. Post-transaction : Redis Pub/Sub + MongoDB activity_log
    """

    # ÉTAPE 1 - ecture du menu pour prix et données
    try:
        col = get_collection("menus")
        menu_doc = col.find_one({"restaurant_id": str(restaurant_id)})
    except Exception as e:
        raise MenuNotFoundError(f"Erreur MongoDB lors de la lecture du menu : {e}")

    if not menu_doc:
        raise MenuNotFoundError(f"Aucun menu trouvé pour le restaurant {restaurant_id}")

    # ÉTAPE 2 - Calcul du total et récupération des snapshots
    order_items_data = []
    total = Decimal("0")

    for req_item in items_requested:
        item_id = req_item["item_id"]
        quantity = req_item["quantity"]

        item_doc = _find_item_in_menu(menu_doc, item_id)
        if not item_doc:
            raise ItemNotFoundError(f"Item '{item_id}' introuvable dans le menu MongoDB")

        item_price = Decimal(str(item_doc["price"]))
        total += item_price * quantity

        order_items_data.append({
            "item_name": item_doc["name"],
            "item_price": item_price,
            "quantity": quantity,
            # snapshot_data : copie FIGÉE de l'item MongoDB - protège contre les futures modifications du menu
            "snapshot_data": {
                "id": item_id,
                "name": item_doc["name"],
                "price": item_doc["price"],
                "description": item_doc.get("description", ""),
                "options": item_doc.get("options", []),
                "tags": item_doc.get("tags", []),
            },
        })

    with transaction.atomic():

        # ÉTAPE 3 vérification solde avant transaction
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
            wallet = Wallet.objects.select_for_update().get(user=user)
        except Restaurant.DoesNotExist:
            raise ValueError(f"Restaurant {restaurant_id} introuvable")

        if wallet.balance < total:
            raise InsufficientFundsError(
                f"Solde insuffisant : {wallet.balance} < {total} requis"
            )

        # 4a. Débit du wallet
        wallet.balance -= total
        wallet.save(update_fields=["balance"])

        # 4b. Création de la commande
        order = Order.objects.create(
            client=user,
            restaurant=restaurant,
            status="pending",
            total_price=total,
            delivery_address=delivery_address,
        )

        # 4c. Création des OrderItems avec snapshot_data
        for item_data in order_items_data:
            OrderItem.objects.create(order=order, **item_data)

        # 4d. WalletTransaction enregistrée dans la même transaction atomique
        WalletTransaction.objects.create(
            wallet=wallet,
            amount=total,
            type="debit",
            order=order,
            description=f"Commande #{order.id} — {restaurant.name}",
        )

    # ÉTAPE 5 (post-transaction) — REDIS : publication statut
    set_order_status(str(order.id), "pending")

    # ÉTAPE 6 (post-transaction) — MONGODB : schéma flexible — log de l'activité
    log_activity(
        str(user.id),
        "order_created",
        {
            "order_id": str(order.id),
            "restaurant": restaurant.name,
            "total": str(total),
            "items_count": len(order_items_data),
        },
    )

    return order
