"""
POSTGRES : ACID requis - historique des paniers (abandonnés ou convertis).
La logique live du panier est dans Redis (TTL 2h), la persistance ici.

Modèles :
- CartSession   : session de panier (un utilisateur peut avoir 1 panier actif)
- CartItem      : ligne de panier avec options choisies (snapshot MongoDB)
- ItemRating    : notation d'un plat (1-5 étoiles) par un client
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import User
from restaurants.models import Restaurant


class CartSession(models.Model):
    """
    Un seul panier actif par utilisateur à la fois.
    """
    STATUS_CHOICES = [
        ("active", "Actif"),
        ("converted", "Converti en commande"),
        ("abandoned", "Abandonné"),
        ("expired", "Expiré"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_sessions")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="cart_sessions")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    # Clé Redis pour ce panier (pattern: cart:{user_id})
    redis_key = models.CharField(max_length=100, blank=True)

    # Snapshot du total calculé (mis à jour à chaque modification)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    items_count = models.PositiveIntegerField(default=0)

    # Tracking conversion
    order_id = models.UUIDField(null=True, blank=True, help_text="FK vers orders.Order si converti")
    abandoned_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_sessions"
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "updated_at"]),
        ]

    def __str__(self):
        return f"Panier {self.user.email} - {self.restaurant.name} [{self.status}]"


class CartItem(models.Model):
    """
    Snapshot complet de l'item MongoDB pour analyse comportementale.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(CartSession, on_delete=models.CASCADE, related_name="items")

    # Référence MongoDB
    item_id = models.CharField(max_length=100, help_text="ID de l'item dans MongoDB menus")
    item_name = models.CharField(max_length=200)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    # Options choisies par l'utilisateur (ex: "Extra sauce", "Taille XL")
    # Structure : [{"label": "Extra sauce DG", "price": 200}, ...]
    selected_options = models.JSONField(default=list)
    options_extra_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # Prix total de cette ligne = (base_price + options_extra_price) * quantity
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Snapshot complet pour analyse (tags, catégorie, image, etc.)
    item_snapshot = models.JSONField(default=dict)

    # Note spéciale du client pour ce plat
    special_instructions = models.CharField(max_length=300, blank=True)

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_items"
        unique_together = [["cart", "item_id"]]  # Un seul slot par item (on modifie qty)

    def save(self, *args, **kwargs):
        """Recalcule automatiquement line_total avant sauvegarde."""
        self.line_total = (self.base_price + self.options_extra_price) * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.item_name} ({self.line_total})"


class ItemRating(models.Model):
    """
    La note du restaurant est calculée à partir des notes de ses plats.
    Un client ne peut noter un plat qu'après une commande livrée contenant ce plat.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="item_ratings")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="item_ratings")

    # Référence MongoDB
    item_id = models.CharField(max_length=100, db_index=True)
    item_name = models.CharField(max_length=200)

    # Note 1-5
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    # Commande d'origine (pour vérifier que le client a bien commandé ce plat)
    order_id = models.UUIDField(help_text="Commande source de cette notation")

    # Métadonnées analytiques
    photos = models.JSONField(default=list, help_text="URLs photos du plat publiées par le client")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "item_ratings"
        # Un client ne peut noter un plat qu'une fois par commande
        unique_together = [["user", "item_id", "order_id"]]
        indexes = [
            models.Index(fields=["item_id"]),
            models.Index(fields=["restaurant", "rating"]),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.item_name} : {self.rating}/5"


class RestaurantRating(models.Model):
    """
    note agrégée d'un restaurant, recalculée automatiquement
    à chaque nouvelle notation de plat. Évite les agrégats lourds à la volée.
    """
    restaurant = models.OneToOneField(
        Restaurant, on_delete=models.CASCADE, related_name="rating"
    )
    avg_rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0,
        help_text="Moyenne calculée depuis item_ratings"
    )
    total_ratings = models.PositiveIntegerField(default=0)
    ratings_distribution = models.JSONField(
        default=dict,
        help_text="{'1': 5, '2': 3, '3': 10, '4': 25, '5': 57}"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "restaurant_ratings"

    def __str__(self):
        return f"{self.restaurant.name} - {self.avg_rating}/5 ({self.total_ratings} avis)"
