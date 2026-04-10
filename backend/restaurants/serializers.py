"""
Note : RestaurantSerializer expose avg_rating/total_ratings calculés
depuis cart.models.RestaurantRating (mis à jour par signal après chaque notation).
"""
from rest_framework import serializers
from .models import Restaurant


class RestaurantSerializer(serializers.ModelSerializer):
    # Note agrégée calculée depuis les notations de plats (cart.models.RestaurantRating)
    avg_rating = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    ratings_distribution = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            "id", "name", "address", "latitude", "longitude",
            "is_active", "avg_rating", "total_ratings",
            "ratings_distribution", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_avg_rating(self, obj):
        try:
            return float(obj.rating.avg_rating)
        except Exception:
            return 0.0

    def get_total_ratings(self, obj):
        try:
            return obj.rating.total_ratings
        except Exception:
            return 0

    def get_ratings_distribution(self, obj):
        try:
            return obj.rating.ratings_distribution
        except Exception:
            return {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}

class RestaurantWriteSerializer(serializers.ModelSerializer):
    """Sérialiseur d'écriture pour créer/modifier un restaurant."""
    class Meta:
        model = Restaurant
        fields = ["name", "address", "latitude", "longitude", "is_active"]

class MenuItemOptionSerializer(serializers.Serializer):
    """Option d'un plat (ex: Extra sauce, Taille XL)."""
    label = serializers.CharField()
    price = serializers.IntegerField()


class MenuItemSerializer(serializers.Serializer):
    """
    Sérialiseur d'un item de menu.
    MONGODB : schéma flexible - les items peuvent avoir des champs optionnels variés.

    Le champ `photos` est une liste d'URLs absolues vers les images stockées sur disque.
    Ces URLs sont gérées via l'endpoint :
      POST/GET/DELETE /api/v1/restaurants/{id}/menu/items/{item_id}/images/
    """
    id = serializers.CharField(required=False)
    name = serializers.CharField()
    price = serializers.IntegerField()
    description = serializers.CharField(required=False, allow_blank=True)

    # Incluses en lecture, ignorées en écriture (le PUT du menu préserve les photos existantes)
    photos = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="URLs des images du plat. Gérez les images via POST /menu/items/{id}/images/",
    )

    options = MenuItemOptionSerializer(many=True, required=False, default=list)
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    available = serializers.BooleanField(required=False, default=True)

    # Champs optionnels
    calories = serializers.IntegerField(required=False)
    allergenes = serializers.ListField(child=serializers.CharField(), required=False)
    promo_price = serializers.IntegerField(required=False)
    promo_ends_at = serializers.DateTimeField(required=False)

    # Champs calculés (lecture seule, mis à jour par cart/signals.py après notation)
    avg_rating = serializers.FloatField(required=False, read_only=True)
    total_ratings = serializers.IntegerField(required=False, read_only=True)


class MenuCategorySerializer(serializers.Serializer):
    """Catégorie d'un menu (ex: Plats principaux, Boissons, Desserts)."""
    name = serializers.CharField()
    items = MenuItemSerializer(many=True)


class MenuSerializer(serializers.Serializer):
    """
    Menu complet d'un restaurant.

    Structure MongoDB :
    {
        "restaurant_id": "uuid",
        "updated_at": "datetime",
        "categories": [
            {
                "name": "Plats principaux",
                "items": [
                    {
                        "id": "uuid",
                        "name": "Poulet DG",
                        "price": 3500,
                        "photos": ["https://.../media/menus/{resto_id}/{item_id}/img.jpg"],
                        "options": [{"label": "Extra sauce", "price": 200}],
                        "avg_rating": 4.3,
                        "total_ratings": 15,
                        ...
                    }
                ]
            }
        ]
    }
    """
    restaurant_id = serializers.CharField(required=False)
    updated_at = serializers.DateTimeField(required=False, read_only=True)
    categories = MenuCategorySerializer(many=True)
