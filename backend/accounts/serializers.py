"""
Sérialiseurs purs — aucune logique métier ici.
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
        read_only_fields = ["id", "created_at"]


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ["id", "balance", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "label", "latitude", "longitude", "is_default"]
        read_only_fields = ["id"]
