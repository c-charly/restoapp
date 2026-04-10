from django.urls import path
from .views import (
    RestaurantListCreateView,
    RestaurantDetailView,
    MenuView,
    MenuItemImagesView,
    MenuItemImagesReorderView,
)

urlpatterns = [
    # Restaurants
    path("", RestaurantListCreateView.as_view(), name="restaurant-list"),
    path("<uuid:pk>/", RestaurantDetailView.as_view(), name="restaurant-detail"),

    # Menus (MongoDB + cache Redis)
    path("<uuid:pk>/menu/", MenuView.as_view(), name="restaurant-menu"),

    # Images des plats (upload multipart - disque + URLs dans MongoDB)
    # GET    - liste des images de l'item
    # POST   - upload (multipart/form-data, champ "images")
    # DELETE - supprimer une image (body: {"image_url": "..."})
    path(
        "<uuid:pk>/menu/items/<str:item_id>/images/",
        MenuItemImagesView.as_view(),
        name="menu-item-images",
    ),
    # PATCH - réordonner les images (body: {"photos": ["url3", "url1", "url2"]})
    path(
        "<uuid:pk>/menu/items/<str:item_id>/images/reorder/",
        MenuItemImagesReorderView.as_view(),
        name="menu-item-images-reorder",
    ),
]
