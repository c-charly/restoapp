"""
Interface d'administration Django pour les données analytiques.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    UserSession, PageView, UserEvent,
    UserAnalyticsProfile, ConversionFunnel,
    SearchQuery, BehavioralAlert,
)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = [
        "session_key_short", "user", "started_at", "duration_display",
        "device_type", "os", "country", "city",
        "page_views_count", "is_bounce",
    ]
    list_filter = ["device_type", "os", "country", "is_bounce"]
    search_fields = ["user__email", "ip_address", "session_key"]
    readonly_fields = ["id", "session_key", "started_at"]
    date_hierarchy = "started_at"
    ordering = ["-started_at"]

    def session_key_short(self, obj):
        return obj.session_key[:12] + "..."
    session_key_short.short_description = "Session"

    def duration_display(self, obj):
        if obj.duration_seconds:
            m, s = divmod(obj.duration_seconds, 60)
            return f"{m}m {s}s"
        return "—"
    duration_display.short_description = "Durée"


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = [
        "method", "path", "http_status_colored", "response_time_ms",
        "user", "timestamp",
    ]
    list_filter = ["method", "http_status"]
    search_fields = ["path", "user__email", "ip_address"]
    readonly_fields = ["id", "timestamp"]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    def http_status_colored(self, obj):
        color = "green" if obj.http_status < 300 else ("orange" if obj.http_status < 500 else "red")
        return format_html('<span style="color:{}">{}</span>', color, obj.http_status)
    http_status_colored.short_description = "Status"


@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ["event_type", "user", "object_type", "object_id", "timestamp"]
    list_filter = ["event_type", "object_type"]
    search_fields = ["user__email", "object_id"]
    readonly_fields = ["id", "timestamp"]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]


@admin.register(UserAnalyticsProfile)
class UserAnalyticsProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user", "loyalty_tier", "engagement_score", "churn_risk_score",
        "total_orders", "total_spent_xaf", "last_seen_at",
        "preferred_device", "primary_city",
    ]
    list_filter = ["loyalty_tier", "preferred_device", "preferred_os"]
    search_fields = ["user__email", "primary_city"]
    readonly_fields = [f.name for f in UserAnalyticsProfile._meta.fields if f.name not in ["id"]]
    ordering = ["-engagement_score"]


@admin.register(BehavioralAlert)
class BehavioralAlertAdmin(admin.ModelAdmin):
    list_display = ["user", "alert_type", "severity_colored", "is_resolved", "created_at"]
    list_filter = ["alert_type", "severity", "is_resolved"]
    search_fields = ["user__email", "message"]
    actions = ["mark_resolved"]
    date_hierarchy = "created_at"

    def severity_colored(self, obj):
        colors = {"info": "blue", "warning": "orange", "critical": "red"}
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colors.get(obj.severity, "black"), obj.severity.upper()
        )
    severity_colored.short_description = "Sévérité"

    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, resolved_at=timezone.now())
    mark_resolved.short_description = "Marquer comme résolues"


@admin.register(ConversionFunnel)
class ConversionFunnelAdmin(admin.ModelAdmin):
    list_display = [
        "user", "restaurant_name", "last_step_name",
        "converted", "order_total", "time_to_convert_seconds", "started_at",
    ]
    list_filter = ["converted", "last_step"]
    search_fields = ["user__email", "restaurant_name"]
    date_hierarchy = "started_at"


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ["query", "user", "results_count", "timestamp"]
    search_fields = ["query", "user__email"]
    list_filter = ["results_count"]
    date_hierarchy = "timestamp"
