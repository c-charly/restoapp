"""
Sérialiseurs
"""
from rest_framework import serializers
from .models import CartSession, CartItem, ItemRating, RestaurantRating


# Panier 

class SelectedOptionSerializer(serializers.Serializer):
    label = serializers.CharField()
    price = serializers.DecimalField(max_digits=8, decimal_places=2)


class AddToCartSerializer(serializers.Serializer):
    """Payload pour ajouter un item au panier."""
    restaurant_id = serializers.UUIDField()
    item_id = serializers.CharField(help_text="ID de l'item dans MongoDB")
    quantity = serializers.IntegerField(min_value=1, default=1)
    selected_options = SelectedOptionSerializer(many=True, required=False, default=list)
    special_instructions = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class UpdateCartItemSerializer(serializers.Serializer):
    """Payload pour modifier la quantité d'un item."""
    quantity = serializers.IntegerField(min_value=0)


class CheckoutSerializer(serializers.Serializer):
    """Payload pour convertir le panier en commande."""
    delivery_address = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = [
            "id", "item_id", "item_name", "base_price", "quantity",
            "selected_options", "options_extra_price", "line_total",
            "special_instructions", "item_snapshot", "added_at",
        ]
        read_only_fields = fields


class CartSessionSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = CartSession
        fields = [
            "id", "restaurant_name", "status", "subtotal", "items_count",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = fields


# Notations

class ItemRatingCreateSerializer(serializers.Serializer):
    """Payload pour noter un plat."""
    item_id = serializers.CharField()
    item_name = serializers.CharField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    photos = serializers.ListField(child=serializers.URLField(), required=False, default=list)
    order_id = serializers.UUIDField(help_text="Commande contenant ce plat")


class ItemRatingSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ItemRating
        fields = [
            "id", "user_email", "item_id", "item_name",
            "rating", "comment", "photos", "order_id", "created_at",
        ]
        read_only_fields = ["id", "user_email", "created_at"]


class RestaurantRatingSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = RestaurantRating
        fields = [
            "restaurant_name", "avg_rating", "total_ratings",
            "ratings_distribution", "updated_at",
        ]
        read_only_fields = fields
