"""
- Gestion des commandes
- Review : TODO : A revoir, la notation d'un plat se fait dans le module cart
"""
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from datetime import datetime, timezone

from core.mongo import get_collection
from core.redis_client import set_order_status
from core.activity_log import log_activity
from .models import Order, WalletTransaction
from .serializers import (
    OrderSerializer, CreateOrderSerializer,
    OrderStatusSerializer, WalletTransactionSerializer,
)
from .services import create_order, InsufficientFundsError, ItemNotFoundError, MenuNotFoundError


# CRÉER UNE COMMANDE

class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["orders"],
        summary="Créer une commande directe (sans panier)",
        description=(
            "1. Lit les items depuis **MongoDB** (menu)\n"
            "2. Vérifie le solde **Wallet**\n"
            "3. `BEGIN TRANSACTION` - Débit, Order, OrderItems, WalletTransaction\n"
            "4. `COMMIT` / `ROLLBACK`\n"
            "5. Publie sur **Redis** Pub/Sub\n\n"
            "Pour une commande avec options et instructions, utilisez le **panier** : "
            "`POST /api/v1/cart/add/` - `POST /api/v1/cart/checkout/`"
        ),
        request=CreateOrderSerializer,
        responses={201: OrderSerializer},
    )
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            order = create_order(
                user=request.user,
                restaurant_id=str(serializer.validated_data["restaurant_id"]),
                items_requested=serializer.validated_data["items"],
                delivery_address=serializer.validated_data.get("delivery_address", ""),
            )
        except InsufficientFundsError as e:
            return Response({"error": str(e), "code": "INSUFFICIENT_FUNDS"}, status=400)
        except (ItemNotFoundError, MenuNotFoundError) as e:
            return Response({"error": str(e), "code": "ITEM_NOT_FOUND"}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

        return Response(OrderSerializer(order).data, status=201)


# LISTE & DÉTAIL

class OrderListView(ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["orders"],
        summary="Mes commandes (client) / toutes les commandes (admin)",
        description=(
            "- **Client** : retourne uniquement ses propres commandes.\n"
            "- **Admin / Staff** : retourne toutes les commandes avec filtre optionnel "
            "`?status=pending` ou `?restaurant_id=uuid`."
        ),
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, required=False),
            OpenApiParameter("restaurant_id", OpenApiTypes.UUID, required=False),
        ],
    )
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            qs = Order.objects.all()
        else:
            qs = Order.objects.filter(client=user)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        restaurant_id = self.request.query_params.get("restaurant_id")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        return qs.select_related("client", "restaurant")\
                 .prefetch_related("items")\
                 .order_by("-created_at")


class OrderDetailView(RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["orders"], summary="Détail d'une commande")
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.role == "admin":
            return Order.objects.all().select_related("client", "restaurant")\
                                      .prefetch_related("items")
        return Order.objects.filter(client=user)\
                            .select_related("client", "restaurant")\
                            .prefetch_related("items")


# CHANGEMENT DE STATUT - réservé admin

class OrderStatusView(APIView):
    permission_classes = [IsAuthenticated]

    # Transitions autorisées par rôle
    ALLOWED_TRANSITIONS = {
        "admin": {
            "pending":    ["confirmed", "cancelled"],
            "confirmed":  ["preparing", "cancelled", "picked_up"],
            "preparing":  ["picked_up", "cancelled"],
            "picked_up":  ["delivering"],
            "delivering": ["delivered"],
        },
        # "driver": {
        #     "confirmed":  ["picked_up"],
        #     "picked_up":  ["delivering"],
        #     "delivering": ["delivered"],
        # },
    }

    @extend_schema(
        tags=["orders"],
        summary="Changer le statut d'une commande",
        request=OrderStatusSerializer,
    )
    def patch(self, request, pk):
        # Vérifier le rôle
        role = getattr(request.user, "role", None)
        if not (request.user.is_staff or role in ("admin")):
            return Response(
                {"error": "Seuls les admins peuvent changer le statut."},
                status=403
            )

        serializer = OrderStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        new_status = serializer.validated_data["status"]
        effective_role = "admin" if (request.user.is_staff or role == "admin") else role

        # Vérifier la transition
        allowed = self.ALLOWED_TRANSITIONS.get(effective_role, {})
        if new_status not in allowed.get(order.status, []):
            return Response({
                "error": (
                    f"Transition '{order.status}' - '{new_status}' non autorisée "
                    f"pour le rôle '{effective_role}'."
                ),
                "current_status": order.status,
                "allowed_next": allowed.get(order.status, []),
            }, status=400)

        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

        # REDIS : notifie les WebSocket clients
        set_order_status(str(order.id), new_status)

        log_activity(
            str(request.user.id),
            "order_status_changed",
            {"order_id": str(order.id), "new_status": new_status, "by_role": effective_role,
             "updated_by": request.user.email},
        )

        return Response({
            "order_id": str(order.id),
            "status": new_status,
            "updated_by": request.user.email,
        })


# ANNULATION - par le client lui-même (seulement si pending)

class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["orders"],
        summary="Annuler sa commande (client, statut pending uniquement)",
        description=(
            "Un client peut annuler sa commande **uniquement si elle est en statut `pending`**.\n\n"
            "Le wallet est **automatiquement remboursé** via une transaction crédit."
        ),
    )
    def post(self, request, pk):
        try:
            order = Order.objects.get(id=pk, client=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        if order.status != "pending":
            return Response({
                "error": f"Impossible d'annuler une commande au statut '{order.status}'. "
                         f"Seule une commande 'pending' peut être annulée.",
            }, status=400)

        from django.db import transaction as db_transaction
        from accounts.models import Wallet

        # remboursement
        with db_transaction.atomic():
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])

            wallet = Wallet.objects.select_for_update().get(user=request.user)
            wallet.balance += order.total_price
            wallet.save(update_fields=["balance"])

            WalletTransaction.objects.create(
                wallet=wallet,
                amount=order.total_price,
                type="credit",
                order=order,
                description=f"Remboursement annulation commande #{order.id}",
            )

        set_order_status(str(order.id), "cancelled")
        log_activity(str(request.user.id), "order_cancelled",
                     {"order_id": str(order.id), "refund": str(order.total_price)})

        return Response({
            "message": "Commande annulée. Remboursement effectué.",
            "order_id": str(order.id),
            "refund_amount": str(order.total_price),
        })


# REVIEW (MongoDB)

class OrderReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["orders"],
        summary="Ajouter une review de commande (MongoDB)",
        description=(
            "Insère la review dans **MongoDB** `reviews`. "
            "Seul un client peut noter sa propre commande **livrée**.\n\n"
            "Pour noter un **plat spécifique** (avec note individuelle), "
            "utilisez `POST /api/v1/cart/rate/`."
        ),
    )
    def post(self, request, pk):
        try:
            order = Order.objects.get(id=pk, client=request.user, status="delivered")
        except Order.DoesNotExist:
            return Response(
                {"error": "Commande introuvable, non livrée ou ne vous appartient pas."},
                status=404
            )

        rating = request.data.get("rating")
        if not rating or not (1 <= int(rating) <= 5):
            return Response({"error": "Rating doit être entre 1 et 5."}, status=400)

        # MONGODB : reviews avec photos optionnelles, sans migration
        review_doc = {
            "order_id": str(order.id),
            "client_id": str(request.user.id),
            "restaurant_id": str(order.restaurant_id),
            "rating": int(rating),
            "comment": request.data.get("comment", ""),
            "photos": request.data.get("photos", []),
            "created_at": datetime.now(timezone.utc),
        }

        try:
            col = get_collection("reviews")
            # Vérifier qu'il n'existe pas déjà une review pour cette commande
            existing = col.find_one({"order_id": str(order.id), "client_id": str(request.user.id)})
            if existing:
                return Response(
                    {"error": "Vous avez déjà reviewé cette commande."},
                    status=409
                )
            result = col.insert_one(review_doc)
            review_doc["_id"] = str(result.inserted_id)
        except Exception as e:
            return Response({"error": f"MongoDB: {e}"}, status=500)

        log_activity(str(request.user.id), "review_posted",
                     {"order_id": str(order.id), "rating": rating})

        return Response(review_doc, status=201)

    @extend_schema(tags=["orders"], summary="Voir la review d'une commande")
    def get(self, request, pk):
        try:
            order = Order.objects.get(id=pk, client=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        try:
            col = get_collection("reviews")
            review = col.find_one(
                {"order_id": str(order.id)},
                {"_id": 0}
            )
            if not review:
                return Response({"review": None, "message": "Aucune review pour cette commande."})
            return Response({"review": review})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
