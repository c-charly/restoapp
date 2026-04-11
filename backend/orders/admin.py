"""
Interface d'administration Django pour les commandes et transactions.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, WalletTransaction


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["id", "item_name", "item_price", "quantity", "line_total_display"]
    fields = ["item_name", "item_price", "quantity", "line_total_display"]
    can_delete = False

    def line_total_display(self, obj):
        return f"{obj.item_price * obj.quantity} XAF"
    line_total_display.short_description = "Total ligne"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id_short", "client", "restaurant", "status_badge",
        "total_price", "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["client__email", "restaurant__name", "id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [OrderItemInline]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    STATUS_COLORS = {
        "pending": "orange", "confirmed": "blue", "preparing": "purple",
        "picked_up": "teal", "delivering": "navy", "delivered": "green", "cancelled": "red",
    }

    def id_short(self, obj):
        return str(obj.id)[:8] + "..."
    id_short.short_description = "ID"

    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, "black")
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Statut"


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ["wallet", "type_badge", "amount", "description", "created_at"]
    list_filter = ["type", "created_at"]
    search_fields = ["wallet__user__email", "description"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]

    def type_badge(self, obj):
        color = "red" if obj.type == "debit" else "green"
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            color, obj.get_type_display()
        )
    type_badge.short_description = "Type"