"""
POSTGRES : les commandes impliquent des transactions financières atomiques.
"""
import uuid
from django.db import models
from accounts.models import User, Wallet
from restaurants.models import Restaurant


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("confirmed", "Confirmée"),
        ("preparing", "En préparation"),
        ("picked_up", "Récupérée"),
        ("delivering", "En livraison"),
        ("delivered", "Livrée"),
        ("cancelled", "Annulée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(User, on_delete=models.PROTECT, related_name="orders")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    delivery_address = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"

    def __str__(self):
        return f"Order {self.id} - {self.status}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    item_name = models.CharField(max_length=200)
    item_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    # snapshot_data : copie figée de l'item MongoDB au moment de la commande
    # Garantit que le prix enregistré ne change pas si le menu est modifié ultérieurement
    snapshot_data = models.JSONField(default=dict)

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.quantity}x {self.item_name}"


class WalletTransaction(models.Model):
    TYPE_CHOICES = [("debit", "Débit"), ("credit", "Crédit")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name="transactions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "wallet_transactions"

    def __str__(self):
        return f"{self.type} {self.amount} XAF - {self.wallet.user.email}"
