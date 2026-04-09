"""
Interface d'administration Django pour les utilisateurs et wallets.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Wallet, Address


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "role_badge", "is_active", "is_staff", "created_at"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering = ["-created_at"]
    readonly_fields = ["id", "created_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations personnelles", {"fields": ("first_name", "last_name", "phone")}),
        ("Rôle et statut", {"fields": ("role", "is_active", "is_staff", "is_superuser")}),
        ("Dates", {"fields": ("created_at", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role"),
        }),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or "—"
    full_name.short_description = "Nom"

    def role_badge(self, obj):
        colors = {"client": "blue", "admin": "red"}
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colors.get(obj.role, "black"),
            obj.get_role_display(),
        )
    role_badge.short_description = "Rôle"


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ["user", "balance_display", "updated_at"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "updated_at"]
    ordering = ["-balance"]

    def balance_display(self, obj):
        color = "green" if obj.balance > 0 else "red"
        return format_html(
            '<span style="color:{};font-weight:bold">{} XAF</span>',
            color, obj.balance
        )
    balance_display.short_description = "Solde"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "label", "latitude", "longitude", "is_default"]
    search_fields = ["user__email", "label"]
    list_filter = ["is_default"]
