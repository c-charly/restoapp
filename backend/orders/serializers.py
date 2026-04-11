"""
Sérialiseurs
"""
from rest_framework import serializers
from .models import Order, OrderItem, WalletTransaction


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["id", "item_name", "item_price", "quantity", "snapshot_data"]
        read_only_fields = ["id"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    client_email = serializers.EmailField(source="client.email", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id", "client_email", "restaurant_name",
            "status", "total_price", "delivery_address",
            "items", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]



class CreateOrderItemSerializer(serializers.Serializer):
    item_id = serializers.CharField(help_text="ID de l'item dans MongoDB")
    quantity = serializers.IntegerField(min_value=1)


class CreateOrderSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    delivery_address = serializers.CharField(max_length=300, required=False, allow_blank=True)
    items = CreateOrderItemSerializer(many=True, min_length=1)


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ["id", "amount", "type", "order", "description", "created_at"]
        read_only_fields = ["id", "created_at"]
