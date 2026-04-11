
"""
CRUD complet : User (profil), Wallet (recharge), Address (CRUD).
"""
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from drf_spectacular.utils import extend_schema
from django.db import transaction

from .serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer,
    WalletSerializer, WalletTopupSerializer, AddressSerializer,
)
from .models import User, Wallet, Address

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["auth"],
        request=RegisterSerializer,
        responses={201: RegisterSerializer},
        summary="Inscription d'un nouvel utilisateur",
        description="Crée un User et génère automatiquement un Wallet via signal Django.",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                RegisterSerializer(user).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# PROFIL UTILISATEUR CONNECTÉ
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        summary="Profil de l'utilisateur connecté",
        description="Retourne les données du profil et le solde du wallet.",
    )
    def get(self, request):
        return Response({
            "user": UserSerializer(request.user).data,
            "wallet": WalletSerializer(request.user.wallet).data,
        })

    @extend_schema(
        tags=["auth"],
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
        summary="Mettre à jour son profil",
        description="Met à jour les champs modifiables : `first_name`, `last_name`, `phone`.",
    )
    def patch(self, request):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserSerializer(request.user).data)
        return Response(serializer.errors, status=400)


# WALLET
class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["wallet"],
        summary="Solde du wallet",
        description="Retourne le solde courant du wallet de l'utilisateur connecté.",
    )
    def get(self, request):
        return Response(WalletSerializer(request.user.wallet).data)


class WalletTopupView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["wallet"],
        request=WalletTopupSerializer,
        responses={200: WalletSerializer},
        summary="Recharger le wallet",
        description=(
            "Crédite le wallet de l'utilisateur connecté.\n\n"
            "Montant minimum : **100**."
        ),
    )
    def post(self, request):
        serializer = WalletTopupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        amount = serializer.validated_data["amount"]

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=request.user)
            wallet.balance += amount
            wallet.save(update_fields=["balance"])

            from orders.models import WalletTransaction
            WalletTransaction.objects.create(
                wallet=wallet,
                amount=amount,
                type="credit",
                description=serializer.validated_data.get("description", "Recharge manuelle"),
            )

        return Response({
            "message": f"Wallet rechargé de {amount}.",
            "wallet": WalletSerializer(wallet).data,
        })


class WalletTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["wallet"],
        summary="Historique des transactions du wallet",
        description="Retourne les 50 dernières transactions (débits et crédits).",
    )
    def get(self, request):
        from orders.models import WalletTransaction
        from orders.serializers import WalletTransactionSerializer
        transactions = WalletTransaction.objects.filter(
            wallet=request.user.wallet
        ).order_by("-created_at")[:50]
        return Response(WalletTransactionSerializer(transactions, many=True).data)


# ADRESSES
class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["addresses"],
        summary="Mes adresses de livraison",
        description="Retourne la liste des adresses enregistrées par l'utilisateur connecté.",
    )
    def get(self, request):
        addresses = Address.objects.filter(user=request.user).order_by("-is_default", "label")
        return Response(AddressSerializer(addresses, many=True).data)

    @extend_schema(
        tags=["addresses"],
        request=AddressSerializer,
        responses={201: AddressSerializer},
        summary="Ajouter une adresse de livraison",
        description=(
            "Crée une nouvelle adresse. Si `is_default=True`, "
            "les autres adresses de l'utilisateur sont automatiquement passées à `is_default=False`."
        ),
    )
    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        # Si is_default, retirer le flag des autres adresses
        if serializer.validated_data.get("is_default"):
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

        address = serializer.save(user=request.user)
        return Response(AddressSerializer(address).data, status=201)


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_address(self, request, pk):
        try:
            return Address.objects.get(id=pk, user=request.user)
        except Address.DoesNotExist:
            return None

    @extend_schema(tags=["addresses"], summary="Détail d'une adresse")
    def get(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return Response({"error": "Adresse introuvable."}, status=404)
        return Response(AddressSerializer(address).data)

    @extend_schema(
        tags=["addresses"],
        request=AddressSerializer,
        responses={200: AddressSerializer},
        summary="Modifier une adresse",
    )
    def patch(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return Response({"error": "Adresse introuvable."}, status=404)

        serializer = AddressSerializer(address, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        if serializer.validated_data.get("is_default"):
            Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

        serializer.save()
        return Response(AddressSerializer(address).data)

    @extend_schema(tags=["addresses"], summary="Supprimer une adresse")
    def delete(self, request, pk):
        address = self._get_address(request, pk)
        if not address:
            return Response({"error": "Adresse introuvable."}, status=404)
        address.delete()
        return Response(status=204)


class SetDefaultAddressView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["addresses"],
        summary="Définir une adresse comme adresse par défaut",
    )
    def patch(self, request, pk):
        try:
            address = Address.objects.get(id=pk, user=request.user)
        except Address.DoesNotExist:
            return Response({"error": "Adresse introuvable."}, status=404)

        Address.objects.filter(user=request.user).update(is_default=False)
        address.is_default = True
        address.save(update_fields=["is_default"])
        return Response(AddressSerializer(address).data)


# ADMIN - Gestion des utilisateurs
class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["admin-users"],
        summary="[Admin] Liste de tous les utilisateurs",
        description="Retourne tous les utilisateurs avec filtrage optionnel par rôle.",
    )
    def get(self, request):
        qs = User.objects.all().order_by("-created_at")
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return Response(UserSerializer(qs[:200], many=True).data)


class AdminUserDetailView(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["admin-users"], summary="[Admin] Détail d'un utilisateur")
    def get(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=404)
        return Response({
            "user": UserSerializer(user).data,
            "wallet": WalletSerializer(user.wallet).data,
        })

    @extend_schema(
        tags=["admin-users"],
        summary="[Admin] Activer / désactiver un utilisateur",
        description="Modifie `is_active` ou `role`.",
    )
    def patch(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=404)

        allowed_fields = {"is_active", "role"}
        for field in allowed_fields:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        return Response(UserSerializer(user).data)