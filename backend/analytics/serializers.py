"""
Sérialiseurs
"""
from rest_framework import serializers
from .models import (
    UserSession, PageView, UserEvent,
    UserAnalyticsProfile, ConversionFunnel,
    SearchQuery, BehavioralAlert,
)


class UserSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True, default=None)

    class Meta:
        model = UserSession
        fields = [
            "id", "user_email", "session_key",
            "started_at", "last_activity_at", "ended_at", "duration_seconds",
            "ip_address", "country", "city",
            "device_type", "os", "os_version", "browser",
            "page_views_count", "events_count", "orders_count", "is_bounce",
            "referrer", "utm_source", "utm_medium", "utm_campaign",
        ]
        read_only_fields = fields


class PageViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageView
        fields = [
            "id", "method", "path", "http_status", "response_time_ms",
            "timestamp", "view_name", "referer",
        ]
        read_only_fields = fields


class UserEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEvent
        fields = [
            "id", "event_type", "object_type", "object_id",
            "properties", "timestamp",
        ]
        read_only_fields = fields


class UserAnalyticsProfileSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserAnalyticsProfile
        fields = [
            "user_email",
            "total_sessions", "total_page_views", "total_events",
            "avg_session_duration_seconds", "avg_pages_per_session",
            "first_seen_at", "last_seen_at", "last_device",
            "total_orders", "total_spent_xaf", "avg_order_value_xaf",
            "orders_cancelled", "orders_delivered", "cart_abandonments",
            "favorite_restaurant_name", "favorite_restaurant_orders",
            "most_active_hour", "most_active_day",
            "preferred_device", "preferred_os",
            "primary_city", "primary_country",
            "engagement_score", "churn_risk_score", "loyalty_tier",
            "total_reviews", "avg_rating_given",
            "orders_by_hour", "orders_by_day",
            "top_search_queries", "top_visited_paths",
            "updated_at",
        ]
        read_only_fields = fields


class BehavioralAlertSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = BehavioralAlert
        fields = [
            "id", "user_email", "alert_type", "severity",
            "message", "details", "is_resolved", "resolved_at", "created_at",
        ]
        read_only_fields = ["id", "user_email", "created_at"]


class ConversionFunnelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversionFunnel
        fields = [
            "id", "restaurant_name", "last_step", "last_step_name",
            "converted", "order_total", "time_to_convert_seconds",
            "abandoned_at_step", "step_timestamps", "started_at", "completed_at",
        ]
        read_only_fields = fields


class TrackEventSerializer(serializers.Serializer):
    """Payload pour tracker un événement depuis le frontend."""
    event_type = serializers.ChoiceField(choices=UserEvent.EVENT_TYPES)
    object_type = serializers.CharField(required=False, allow_blank=True, default="")
    object_id = serializers.CharField(required=False, allow_blank=True, default="")
    properties = serializers.DictField(required=False, default=dict)


class TrackSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500)
    results_count = serializers.IntegerField(required=False, default=0)
    filters = serializers.DictField(required=False, default=dict)
