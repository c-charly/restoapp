from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    RegisterView, MeView,
    WalletView, WalletTopupView, WalletTransactionsView,
    AddressListCreateView, AddressDetailView, SetDefaultAddressView,
    AdminUserListView, AdminUserDetailView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", MeView.as_view(), name="me"),

    # Wallet
    path("wallet/", WalletView.as_view(),             name="wallet"),
    path("wallet/topup/", WalletTopupView.as_view(),        name="wallet-topup"),
    path("wallet/transactions/", WalletTransactionsView.as_view(), name="wallet-transactions"),

    # Adresses
    path("addresses/", AddressListCreateView.as_view(), name="address-list"),
    path("addresses/<uuid:pk>/", AddressDetailView.as_view(), name="address-detail"),
    path("addresses/<uuid:pk>/default/", SetDefaultAddressView.as_view(), name="address-default"),

    # Admin
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<uuid:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
]
