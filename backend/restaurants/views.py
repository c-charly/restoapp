"""
- Profils Restaurant : PostgreSQL
- Menus (lecture/écriture) : MongoDB avec cache Redis (TTL 10 min)
- Images des plats : upload multipart - disque + URLs dans MongoDB
"""
import uuid as uuid_lib
from datetime import datetime, timezone

from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from core.mongo import get_collection
from core.redis_client import get_cached_menu, set_cached_menu, invalidate_menu_cache
from core.activity_log import log_activity
from .models import Restaurant
from .serializers import RestaurantSerializer, RestaurantWriteSerializer, MenuSerializer
from .image_service import (
    upload_item_images, delete_item_image,
    reorder_item_images, get_item_images,
)

# RESTAURANTS - CRUD
class RestaurantListCreateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(tags=["restaurants"], summary="Liste des restaurants actifs")
    def get(self, request):
        qs = Restaurant.objects.filter(is_active=True).select_related("rating").order_by("name")
        return Response(RestaurantSerializer(qs, many=True).data)

    @extend_schema(
        tags=["restaurants"],
        request=RestaurantWriteSerializer,
        responses={201: RestaurantSerializer},
        summary="[Admin] Créer un restaurant",
        description="Crée un restaurant. Le propriétaire est l'utilisateur connecté.",
    )
    def post(self, request):
        if not (request.user.is_authenticated and (request.user.is_staff or request.user.role == "admin")):
            return Response({"error": "Réservé aux administrateurs."}, status=403)

        serializer = RestaurantWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        restaurant = serializer.save(owner=request.user)
        log_activity(str(request.user.id), "restaurant_created",
                     {"restaurant_id": str(restaurant.id), "name": restaurant.name})
        return Response(RestaurantSerializer(restaurant).data, status=201)


class RestaurantDetailView(APIView):
    permission_classes = [AllowAny]

    def _get_restaurant(self, pk):
        try:
            return Restaurant.objects.select_related("rating").get(id=pk)
        except Restaurant.DoesNotExist:
            return None

    @extend_schema(tags=["restaurants"], summary="Détail d'un restaurant")
    def get(self, request, pk):
        restaurant = self._get_restaurant(pk)
        if not restaurant:
            return Response({"error": "Restaurant introuvable."}, status=404)
        return Response(RestaurantSerializer(restaurant).data)

    @extend_schema(
        tags=["restaurants"],
        request=RestaurantWriteSerializer,
        responses={200: RestaurantSerializer},
        summary="[Admin/Owner] Modifier un restaurant",
    )
    def patch(self, request, pk):
        restaurant = self._get_restaurant(pk)
        if not restaurant:
            return Response({"error": "Restaurant introuvable."}, status=404)

        if not request.user.is_authenticated:
            return Response({"error": "Authentification requise."}, status=401)
        if not (request.user.is_staff or restaurant.owner == request.user):
            return Response({"error": "Accès refusé."}, status=403)

        serializer = RestaurantWriteSerializer(restaurant, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(RestaurantSerializer(restaurant).data)

    @extend_schema(tags=["restaurants"], summary="[Admin] Désactiver / supprimer un restaurant")
    def delete(self, request, pk):
        restaurant = self._get_restaurant(pk)
        if not restaurant:
            return Response({"error": "Restaurant introuvable."}, status=404)

        if not (request.user.is_authenticated and request.user.is_staff):
            return Response({"error": "Réservé aux administrateurs."}, status=403)

        # Soft delete (désactivation) pour préserver l'intégrité FK des commandes
        restaurant.is_active = False
        restaurant.save(update_fields=["is_active"])
        return Response({"message": "Restaurant désactivé."}, status=200)

# MENUS
class MenuView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["restaurants"],
        summary="Menu d'un restaurant (Redis - MongoDB)",
        description=(
            "1. Vérifie Redis `menu:{id}` (TTL 10 min)\n"
            "2. Si absent - lit MongoDB - stocke en Redis\n"
            "3. Retourne le menu avec photos, avg_rating, options par item."
        ),
    )
    def get(self, request, pk):
        restaurant_id = str(pk)
        # REDIS : performance temps réel - cache avant MongoDB
        cached = get_cached_menu(restaurant_id)
        if cached:
            cached["_cache"] = "HIT (Redis)"
            return Response(cached)

        try:
            col = get_collection("menus")
            menu = col.find_one({"restaurant_id": restaurant_id})
            if not menu:
                return Response({"error": "Menu introuvable."}, status=404)
            menu["_id"] = str(menu["_id"])
            menu["_cache"] = "MISS (MongoDB)"
            set_cached_menu(restaurant_id, menu)
            return Response(menu)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @extend_schema(
        tags=["restaurants"],
        request=MenuSerializer,
        summary="[Owner/Admin] Créer / mettre à jour le menu",
        description=(
            "Upsert du document menu dans MongoDB. Les photos existantes sont préservées.\n\n"
            "Chaque item reçoit un `id` UUID auto-généré si absent.\n\n"
            "Pour uploader les images d'un plat : "
            "`POST /restaurants/{id}/menu/items/{item_id}/images/`"
        ),
    )
    def put(self, request, pk):
        restaurant_id = str(pk)
        try:
            restaurant = Restaurant.objects.get(id=pk)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant introuvable."}, status=404)

        if not request.user.is_authenticated:
            return Response({"error": "Authentification requise."}, status=401)
        if not (request.user.is_staff or restaurant.owner == request.user):
            return Response({"error": "Accès refusé."}, status=403)

        serializer = MenuSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        menu_data = dict(serializer.validated_data)

        # Auto-générer les IDs des items sans ID
        for category in menu_data.get("categories", []):
            for item in category.get("items", []):
                if not item.get("id"):
                    item["id"] = str(uuid_lib.uuid4())
                if "photos" not in item:
                    item["photos"] = []

        menu_data["restaurant_id"] = restaurant_id
        menu_data["updated_at"] = datetime.now(timezone.utc)

        try:
            col = get_collection("menus")
            # Préserver les photos existantes
            existing = col.find_one({"restaurant_id": restaurant_id})
            if existing:
                existing_photo_map = {
                    it["id"]: it["photos"]
                    for cat in existing.get("categories", [])
                    for it in cat.get("items", [])
                    if it.get("id") and it.get("photos")
                }
                for category in menu_data.get("categories", []):
                    for item in category.get("items", []):
                        iid = item.get("id", "")
                        if iid in existing_photo_map and not item.get("photos"):
                            item["photos"] = existing_photo_map[iid]

            col.update_one({"restaurant_id": restaurant_id}, {"$set": menu_data}, upsert=True)
        except Exception as e:
            return Response({"error": f"MongoDB: {e}"}, status=500)

        invalidate_menu_cache(restaurant_id)

        log_activity(str(request.user.id), "menu_updated",
                     {"restaurant_id": restaurant_id, "name": restaurant.name})

        return Response({
            "status": "Menu mis à jour.",
            "restaurant_id": restaurant_id,
            "tip": f"Uploadez les images via POST /api/v1/restaurants/{pk}/menu/items/{{item_id}}/images/",
        })

    @extend_schema(tags=["restaurants"], summary="[Owner/Admin] Supprimer le menu")
    def delete(self, request, pk):
        restaurant_id = str(pk)
        try:
            restaurant = Restaurant.objects.get(id=pk)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant introuvable."}, status=404)

        if not (request.user.is_authenticated and
                (request.user.is_staff or restaurant.owner == request.user)):
            return Response({"error": "Accès refusé."}, status=403)

        col = get_collection("menus")
        col.delete_one({"restaurant_id": restaurant_id})
        invalidate_menu_cache(restaurant_id)
        log_activity(str(request.user.id), "menu_deleted", {"restaurant_id": restaurant_id})
        return Response({"message": "Menu supprimé."}, status=200)


# IMAGES DES PLATS - disque + URLs dans MongoDB
class MenuItemImagesView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [IsAuthenticated]

    def _check_owner(self, request, pk):
        try:
            restaurant = Restaurant.objects.get(id=pk)
        except Restaurant.DoesNotExist:
            return None, Response({"error": "Restaurant introuvable."}, status=404)
        if not (request.user.is_staff or restaurant.owner == request.user):
            return None, Response({"error": "Accès refusé."}, status=403)
        return restaurant, None

    @extend_schema(
        tags=["restaurants"],
        summary="Voir les images d'un plat",
        description="Retourne les URLs des images existantes, le slot count et le max autorisé.",
    )
    def get(self, request, pk, item_id):
        try:
            result = get_item_images(str(pk), item_id)
            return Response(result)
        except ValueError as e:
            return Response({"error": str(e)}, status=404)

    @extend_schema(
        tags=["restaurants"],
        summary="[Owner/Admin] Uploader des images (multipart/form-data)",
        description=(
            "Champ : `images` (un ou plusieurs fichiers).\n"
            "Extensions : `.jpg .jpeg .png .webp` - Max **5 Mo** par image - Max **5 images** par plat.\n\n"
        ),
    )
    def post(self, request, pk, item_id):
        restaurant, err = self._check_owner(request, pk)
        if err:
            return err

        image_files = request.FILES.getlist("images")
        if not image_files:
            return Response({"error": "Aucun fichier reçu. Utilisez le champ `images`."}, status=400)

        try:
            all_photos = upload_item_images(str(pk), item_id, image_files, request)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except RuntimeError as e:
            return Response({"error": str(e)}, status=500)

        log_activity(str(request.user.id), "item_images_uploaded",
                     {"restaurant_id": str(pk), "item_id": item_id, "count": len(image_files)})

        return Response({
            "status": "Images uploadées.",
            "item_id": item_id,
            "photos": all_photos,
            "photos_count": len(all_photos),
            "uploaded_count": len(image_files),
        }, status=201)

    @extend_schema(
        tags=["restaurants"],
        summary="[Owner/Admin] Supprimer une image",
        description="Body JSON : `{\"image_url\": \"https://...\"}`. Supprime le fichier et l'URL.",
    )
    def delete(self, request, pk, item_id):
        restaurant, err = self._check_owner(request, pk)
        if err:
            return err

        image_url = request.data.get("image_url") or request.query_params.get("image_url")
        if not image_url:
            return Response({"error": "Paramètre `image_url` requis."}, status=400)

        try:
            remaining = delete_item_image(str(pk), item_id, image_url)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        log_activity(
            str(request.user.id),
            "item_image_deleted",
            {"restaurant_id": str(pk), "item_id": item_id, "deleted_url": image_url},
        )
        return Response({
            "status": "Image supprimée.",
            "item_id": item_id,
            "photos": remaining,
            "photos_count": len(remaining),
        })


class MenuItemImagesReorderView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["restaurants"],
        summary="[Owner/Admin] Réordonner les images d'un plat",
        description="Body JSON : `{\"photos\": [\"url3\", \"url1\", \"url2\"]}`. Doit contenir toutes les URLs existantes.",
    )
    def patch(self, request, pk, item_id):
        try:
            restaurant = Restaurant.objects.get(id=pk)
        except Restaurant.DoesNotExist:
            return Response({"error": "Restaurant introuvable."}, status=404)
        if not (request.user.is_staff or restaurant.owner == request.user):
            return Response({"error": "Accès refusé."}, status=403)

        ordered_urls = request.data.get("photos")
        if not ordered_urls or not isinstance(ordered_urls, list):
            return Response({"error": "Champ `photos` requis (liste d'URLs)."}, status=400)

        try:
            result = reorder_item_images(str(pk), item_id, ordered_urls)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)

        return Response({
            "status": "Ordre mis à jour.",
            "item_id": item_id,
            "photos": result,
        })