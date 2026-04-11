"""
Interface d'administration Django pour le panier et les notations.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import CartSession, CartItem, ItemRating, RestaurantRating


@admin.register(CartSession)
class CartSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "restaurant", "status", "subtotal", "items_count", "order_id", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email", "restaurant__name"]
    readonly_fields = ["id", "created_at"]
    date_hierarchy = "created_at"


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["item_name", "cart", "quantity", "base_price", "options_extra_price", "line_total"]
    search_fields = ["item_name", "cart__user__email"]
    readonly_fields = ["id", "added_at", "line_total"]


@admin.register(ItemRating)
class ItemRatingAdmin(admin.ModelAdmin):
    list_display = ["user", "item_name", "rating_stars", "restaurant", "created_at"]
    list_filter = ["rating", "restaurant"]
    search_fields = ["user__email", "item_name"]
    readonly_fields = ["id", "created_at"]
    date_hierarchy = "created_at"

    def rating_stars(self, obj):
        stars = "⭐" * obj.rating + "☆" * (5 - obj.rating)
        color = "green" if obj.rating >= 4 else ("orange" if obj.rating == 3 else "red")
        return format_html('<span style="color:{}">{}</span>', color, stars)
    rating_stars.short_description = "Note"


@admin.register(RestaurantRating)
class RestaurantRatingAdmin(admin.ModelAdmin):
    list_display = ["restaurant", "avg_rating_display", "total_ratings", "updated_at"]
    readonly_fields = ["updated_at"]
    ordering = ["-avg_rating"]

    def avg_rating_display(self, obj):
        color = "green" if float(obj.avg_rating) >= 4 else "orange"
        return format_html('<span style="color:{};font-weight:bold">⭐ {}/5</span>', color, obj.avg_rating)
    avg_rating_display.short_description = "Note"
