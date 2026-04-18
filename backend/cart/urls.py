from django.urls import path
from .views import (
    CartView, CartAddView, CartItemView, CheckoutView, CartAbandon,
    ItemRatingView, ItemRatingDetailView,
    RestaurantRatingView, ItemRatingsListView,
)

urlpatterns = [
    # Panier
    path("", CartView.as_view(), name="cart"),
    path("add/", CartAddView.as_view(), name="cart-add"),
    path("abandon/", CartAbandon.as_view(), name="cart-abandon"),

    # PATCH  -> modifier quantité (quantity=0 supprime)
    # DELETE -> retirer un item
    path("item/<str:item_id>/", CartItemView.as_view(), name="cart-item"),

    path("checkout/", CheckoutView.as_view(), name="cart-checkout"),

    # Notations
    path("rate/", ItemRatingView.as_view(), name="item-rate"),
    path("rate/<uuid:pk>/", ItemRatingDetailView.as_view(), name="item-rate-detail"),

    # Note agrégée d'un restaurant
    path("restaurant/<uuid:restaurant_id>/rating/",
         RestaurantRatingView.as_view(), name="restaurant-rating"),

    # Toutes les notes d'un plat
    path("item/<str:item_id>/ratings/",
         ItemRatingsListView.as_view(), name="item-ratings"),
]
