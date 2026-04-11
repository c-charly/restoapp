"""
Sérialiseurs
"""
from rest_framework import serializers
from .models import User, Wallet, Address


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "email", "phone", "first_name", "last_name", "role", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "phone", "first_name", "last_name", "role", "created_at"]
        read_only_fields = ["id", "email", "created_at"]


class UserUpdateSerializer(serializers.ModelSerializer):
    """Seuls first_name, last_name, phone sont modifiables par l'utilisateur lui-même."""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "balance", "updated_at"]
        read_only_fields = ["id", "balance", "updated_at"]


class WalletTopupSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        min_value=100,
        help_text="Montant à créditer (minimum 100)",
    )
    description = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        default="Recharge manuelle",
    )


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "label", "latitude", "longitude", "is_default"]
        read_only_fields = ["id"]
