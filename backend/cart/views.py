"""
Panier (Redis live) + Notation des plats.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.db.models import Avg, Count
from django.utils import timezone as dj_timezone

from orders.serializers import OrderSerializer
from .serializers import (
    AddToCartSerializer, UpdateCartItemSerializer, CheckoutSerializer,
    ItemRatingCreateSerializer, ItemRatingSerializer, RestaurantRatingSerializer,
)
from .services import (
    get_or_create_cart, add_item_to_cart, update_cart_item,
    clear_user_cart, checkout, delete_cart,
    CartError, InsufficientFundsError, RestaurantMismatchError, EmptyCartError,
)
from .models import ItemRating, RestaurantRating, CartSession
from .redis_cart import get_cart
from restaurants.models import Restaurant
from orders.models import Order, OrderItem


# PANIER
class CartView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["cart"],
        summary="Voir son panier",
        description=(
            "Retourne le panier actif depuis **Redis** (TTL 2h). "
            "Inclut les items, options choisies, instructions spéciales et subtotal."
        ),
    )
    def get(self, request):
        cart = get_cart(str(request.user.id))
        if not cart:
            return Response({"cart": None, "message": "Aucun panier actif."})
        return Response({"cart": cart})

    @extend_schema(
        tags=["cart"],
        summary="Vider le panier",
        description="Vide tous les items du panier Redis. Le restaurant reste sélectionné.",
    )
    def delete(self, request):
        try:
            cart = clear_user_cart(request.user)
            return Response({"cart": cart, "message": "Panier vidé."})
        except CartError as e:
            return Response({"error": str(e)}, status=400)

class CartAbandon(APIView):

    @extend_schema(
        tags=["cart"],
        summary="Abandonner le panier",
    )
    def delete(self, request):
        try:
            CartSession.objects.filter(user=request.user, status="active").update(
                status="abandoned",
                abandoned_at=dj_timezone.now(),
            )
            status = delete_cart(str(request.user.id)) # suppression complet du panier
            return Response({"status": status, "message": "Suppression du panier."})
        except CartError as e:
            return Response({"error": str(e)}, status=400)


class CartAddView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["cart"],
        summary="Ajouter un item au panier (avec options)",
        description=(
            "Ajoute un item depuis le menu MongoDB dans le panier Redis.\n\n"
            "- Valide l'item et ses options\n"
            "- Calcule le prix exact (base + options choisies)\n"
            "- Stocke un snapshot complet pour analyse comportementale\n"
            "- Permet des instructions spéciales (ex: 'sans oignon')\n\n"
            "**REDIS** : panier stocké en Redis, TTL 2h renouvelé à chaque modification."
        ),
        request=AddToCartSerializer,
    )
    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        d = serializer.validated_data
        try:
            cart = add_item_to_cart(
                user=request.user,
                restaurant_id=str(d["restaurant_id"]),
                item_id=d["item_id"],
                quantity=d["quantity"],
                selected_options=[dict(o) for o in d.get("selected_options", [])],
                special_instructions=d.get("special_instructions", ""),
            )
            return Response({"cart": cart, "message": "Item ajouté au panier."})
        except RestaurantMismatchError as e:
            return Response({"error": str(e), "code": "RESTAURANT_MISMATCH"}, status=409)
        except CartError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class CartItemView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["cart"],
        summary="Modifier la quantité d'un item",
        description="`quantity=0` supprime l'item du panier.",
        request=UpdateCartItemSerializer,
    )
    def patch(self, request, item_id):
        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            cart = update_cart_item(request.user, item_id, serializer.validated_data["quantity"])
            return Response({"cart": cart})
        except CartError as e:
            return Response({"error": str(e)}, status=400)

    @extend_schema(tags=["cart"], summary="Retirer un item du panier")
    def delete(self, request, item_id):
        try:
            cart = update_cart_item(request.user, item_id, 0)
            return Response({"cart": cart, "message": "Item retiré."})
        except CartError as e:
            return Response({"error": str(e)}, status=400)


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["cart"],
        summary="Checkout - Convertir le panier en commande",
        description=(
            "**Opération atomique complète :**\n\n"
            "1. Revalide tous les prix depuis **MongoDB** (sécurité)\n"
            "2. Vérifie le solde **Wallet** (PostgreSQL)\n"
            "3. `BEGIN TRANSACTION` :\n"
            "   - Débit Wallet\n"
            "   - Création Order + OrderItems (snapshot avec options choisies)\n"
            "   - WalletTransaction\n"
            "   - CartSession - `converted`\n"
            "4. `COMMIT` / `ROLLBACK`\n"
            "5. Supprime le panier **Redis**\n"
            "6. Publie statut sur **Redis** Pub/Sub - WebSocket"
        ),
        request=CheckoutSerializer,
        responses={201: OrderSerializer},
    )
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            order = checkout(
                user=request.user,
                delivery_address=serializer.validated_data.get("delivery_address", ""),
            )
            return Response(OrderSerializer(order).data, status=201)
        except InsufficientFundsError as e:
            return Response({"error": str(e), "code": "INSUFFICIENT_FUNDS"}, status=400)
        except EmptyCartError as e:
            return Response({"error": str(e), "code": "EMPTY_CART"}, status=400)
        except CartError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# NOTATION DES PLATS

class ItemRatingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ratings"],
        summary="Lister / noter un plat (GET: mes notes, POST: noter)",
    )
    def get(self, request):
        """Liste les notes données par l'utilisateur connecté."""
        ratings = ItemRating.objects.filter(user=request.user).order_by("-created_at")[:50]
        return Response(ItemRatingSerializer(ratings, many=True).data)

    @extend_schema(
        tags=["ratings"],
        summary="Noter un plat (1-5 étoiles)",
        description=(
            "Un client peut noter un plat uniquement après une commande **livrée** "
            "contenant ce plat.\n\n"
            "La note du restaurant est **automatiquement recalculée** via signal Django.\n\n"
            "Les notes alimentent le moteur de **recommandation** de la page d'accueil."
        ),
        request=ItemRatingCreateSerializer,
    )
    def post(self, request):
        serializer = ItemRatingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        d = serializer.validated_data
        order_id = d["order_id"]

        # Vérifier que la commande appartient à l'utilisateur et est livrée
        try:
            order = Order.objects.get(id=order_id, client=request.user, status="delivered")
        except Order.DoesNotExist:
            return Response(
                {"error": "Commande introuvable, non livrée ou ne vous appartient pas."},
                status=404
            )

        # Vérifier que ce plat était dans la commande
        item_in_order = (
            order.items.filter(snapshot_data__id=d["item_id"]).exists()
            or order.items.filter(item_name__iexact=d["item_name"]).exists()
        )
        if not item_in_order:
            return Response({"error": "Ce plat ne fait pas partie de cette commande."}, status=400)

        # Créer ou mettre à jour la notation
        rating, created = ItemRating.objects.update_or_create(
            user=request.user,
            item_id=d["item_id"],
            order_id=order_id,
            defaults={
                "item_name": d["item_name"],
                "restaurant": order.restaurant,
                "rating": d["rating"],
                "comment": d.get("comment", ""),
                "photos": d.get("photos", []),
            },
        )

        # Mettre à jour la note de l'item dans MongoDB
        try:
            from core.mongo import get_collection
            agg = ItemRating.objects.filter(item_id=d["item_id"]).aggregate(
                avg=Avg("rating"), total=Count("id")
            )
            get_collection("menus").update_many(
                {"categories.items.id": d["item_id"]},
                {"$set": {
                    "categories.$[].items.$[item].avg_rating": round(float(agg["avg"] or 0), 2),
                    "categories.$[].items.$[item].total_ratings": agg["total"] or 0,
                }},
                array_filters=[{"item.id": d["item_id"]}],
            )
        except Exception:
            pass

        # TODO : Tracker événement analytique 
        # try:
        #     from analytics.models import UserEvent
        #     UserEvent.objects.create(
        #         user=request.user,
        #         event_type="review_submitted",
        #         object_type="menu_item",
        #         object_id=d["item_id"],
        #         properties={
        #             "item_name": d["item_name"],
        #             "rating": d["rating"],
        #             "restaurant_id": str(order.restaurant_id),
        #             "order_id": str(order_id),
        #         },
        #     )
        # except Exception:
        #     pass

        return Response(
            ItemRatingSerializer(rating).data,
            status=201 if created else 200
        )


class ItemRatingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_rating(self, request, pk):
        try:
            return ItemRating.objects.get(id=pk, user=request.user)
        except ItemRating.DoesNotExist:
            return None

    @extend_schema(tags=["ratings"], summary="Détail d'une notation")
    def get(self, request, pk):
        rating = self._get_rating(request, pk)
        if not rating:
            return Response({"error": "Notation introuvable."}, status=404)
        return Response(ItemRatingSerializer(rating).data)

    @extend_schema(tags=["ratings"], summary="Modifier une notation (commentaire / note)")
    def patch(self, request, pk):
        rating = self._get_rating(request, pk)
        if not rating:
            return Response({"error": "Notation introuvable."}, status=404)

        allowed = {"rating", "comment", "photos"}
        for field in allowed:
            if field in request.data:
                setattr(rating, field, request.data[field])
        rating.save()
        return Response(ItemRatingSerializer(rating).data)

    @extend_schema(tags=["ratings"], summary="Supprimer une notation")
    def delete(self, request, pk):
        rating = self._get_rating(request, pk)
        if not rating:
            return Response({"error": "Notation introuvable."}, status=404)
        rating.delete()
        return Response(status=204)


class RestaurantRatingView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ratings"],
        summary="Note agrégée d'un restaurant",
        description=(
            "Note moyenne calculée depuis toutes les notations des plats du restaurant, "
            "avec distribution étoiles 1-5."
        ),
    )
    def get(self, request, restaurant_id):
        try:
            r = RestaurantRating.objects.select_related("restaurant").get(
                restaurant_id=restaurant_id
            )
            return Response(RestaurantRatingSerializer(r).data)
        except RestaurantRating.DoesNotExist:
            return Response({"avg_rating": 0, "total_ratings": 0,
                             "ratings_distribution": {"1":0,"2":0,"3":0,"4":0,"5":0},
                             "message": "Aucune note pour ce restaurant."})


class ItemRatingsListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["ratings"],
        summary="Notes et avis d'un plat",
        description="Liste les 50 dernières notes pour un item_id MongoDB donné.",
    )
    def get(self, request, item_id):
        ratings = ItemRating.objects.filter(item_id=item_id)\
                                    .select_related("user")\
                                    .order_by("-created_at")
        agg = ratings.aggregate(avg=Avg("rating"), total=Count("id"))
        return Response({
            "item_id": item_id,
            "avg_rating": round(float(agg["avg"] or 0), 2),
            "total_ratings": agg["total"] or 0,
            "ratings": ItemRatingSerializer(ratings[:50], many=True).data,
        })
