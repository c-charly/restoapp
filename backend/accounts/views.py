"""
Vues d'authentification : inscription, JWT
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from .serializers import RegisterSerializer, UserSerializer, WalletSerializer


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


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="Profil de l'utilisateur connecté")
    def get(self, request):
        user_data = UserSerializer(request.user).data
        wallet_data = WalletSerializer(request.user.wallet).data
        return Response({"user": user_data, "wallet": wallet_data})
