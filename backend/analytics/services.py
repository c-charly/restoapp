"""
Services d'agrégation - calculent et consolident les profils analytiques.

POSTGRES : toutes les agrégations SQL (COUNT, AVG, SUM, GROUP BY, annotation).
MONGODB  : lecture des reviews et logs pour enrichissement.
REDIS    : lecture des compteurs temps réel.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.db.models import (
    Count, Sum, Avg, Max, Min, F, Q,
    FloatField, DecimalField, IntegerField,
)
from django.db.models.functions import (
    TruncHour, TruncDay, TruncWeek, TruncMonth,
    ExtractHour, ExtractWeekDay,
)
from django.utils import timezone

from accounts.models import User
from orders.models import Order, WalletTransaction
from .models import (
    UserSession, PageView, UserEvent, UserAnalyticsProfile,
    ConversionFunnel, SearchQuery, BehavioralAlert,
)

logger = logging.getLogger("analytics.services")


# MISE À JOUR DU PROFIL ANALYTIQUE D'UN UTILISATEUR

def refresh_user_analytics_profile(user: User) -> UserAnalyticsProfile:
    """
    Recalcule et persiste le profil analytique complet d'un utilisateur.
    POSTGRES : agrégations SQL complexes sur sessions, commandes, événements.
    """
    profile, _ = UserAnalyticsProfile.objects.get_or_create(user=user)

    # Sessions
    sessions_qs = UserSession.objects.filter(user=user)
    session_agg = sessions_qs.aggregate(
        total=Count("id"),
        avg_duration=Avg("duration_seconds"),
        avg_pages=Avg("page_views_count"),
        first_seen=Min("started_at"),
        last_seen=Max("last_activity_at"),
    )

    profile.total_sessions = session_agg["total"] or 0
    profile.avg_session_duration_seconds = int(session_agg["avg_duration"] or 0)
    profile.avg_pages_per_session = round(session_agg["avg_pages"] or 0, 2)
    profile.first_seen_at = session_agg["first_seen"]
    profile.last_seen_at = session_agg["last_seen"]

    # Dernier device et IP connus
    last_session = sessions_qs.order_by("-started_at").first()
    if last_session:
        profile.last_device = last_session.device_type
        profile.last_active_ip = last_session.ip_address

    # IP connues (liste unique)
    known_ips = list(
        sessions_qs.exclude(ip_address__isnull=True)
        .values_list("ip_address", flat=True)
        .distinct()[:50]
    )
    profile.known_ips = known_ips

    # Page views & Events
    profile.total_page_views = PageView.objects.filter(user=user).count()
    profile.total_events = UserEvent.objects.filter(user=user).count()

    # Commandes
    orders_agg = Order.objects.filter(client=user).aggregate(
        total=Count("id"),
        total_spent=Sum("total_price"),
        avg_value=Avg("total_price"),
        cancelled=Count("id", filter=Q(status="cancelled")),
        delivered=Count("id", filter=Q(status="delivered")),
    )
    profile.total_orders = orders_agg["total"] or 0
    profile.total_spent_xaf = orders_agg["total_spent"] or Decimal("0")
    profile.avg_order_value_xaf = orders_agg["avg_value"] or Decimal("0")
    profile.orders_cancelled = orders_agg["cancelled"] or 0
    profile.orders_delivered = orders_agg["delivered"] or 0

    # Restaurant favori
    fav = (
        Order.objects.filter(client=user)
        .values("restaurant__id", "restaurant__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
        .first()
    )
    if fav:
        profile.favorite_restaurant_id = fav["restaurant__id"]
        profile.favorite_restaurant_name = fav["restaurant__name"] or ""
        profile.favorite_restaurant_orders = fav["cnt"]

    # Habitudes horaires
    # Commandes par heure (0-23)
    by_hour = dict(
        Order.objects.filter(client=user)
        .annotate(h=ExtractHour("created_at"))
        .values("h")
        .annotate(cnt=Count("id"))
        .values_list("h", "cnt")
    )
    profile.orders_by_hour = {str(k): v for k, v in by_hour.items()}
    if by_hour:
        profile.most_active_hour = max(by_hour, key=by_hour.get)

    # Commandes par jour de la semaine (1=Dimanche ... 7=Samedi en Django)
    by_day = dict(
        Order.objects.filter(client=user)
        .annotate(d=ExtractWeekDay("created_at"))
        .values("d")
        .annotate(cnt=Count("id"))
        .values_list("d", "cnt")
    )
    profile.orders_by_day = {str(k): v for k, v in by_day.items()}
    if by_day:
        profile.most_active_day = max(by_day, key=by_day.get)

    # Device préféré
    pref_device = (
        sessions_qs.values("device_type")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
        .first()
    )
    if pref_device:
        profile.preferred_device = pref_device["device_type"]

    pref_os = (
        sessions_qs.values("os")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
        .first()
    )
    if pref_os:
        profile.preferred_os = pref_os["os"]

    # Localisation principale
    pref_city = (
        sessions_qs.exclude(city="")
        .values("city")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
        .first()
    )
    if pref_city:
        profile.primary_city = pref_city["city"]

    pref_country = (
        sessions_qs.exclude(country="")
        .values("country")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
        .first()
    )
    if pref_country:
        profile.primary_country = pref_country["country"]

    # Top recherches
    top_searches = list(
        SearchQuery.objects.filter(user=user)
        .values("query_normalized")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:10]
        .values("query_normalized", "cnt")
    )
    profile.top_search_queries = [
        {"query": s["query_normalized"], "count": s["cnt"]} for s in top_searches
    ]

    # Top paths visités
    top_paths = list(
        PageView.objects.filter(user=user)
        .values("path")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:15]
        .values("path", "cnt")
    )
    profile.top_visited_paths = [
        {"path": p["path"], "count": p["cnt"]} for p in top_paths
    ]

    # Reviews (MongoDB)
    try:
        from core.mongo import get_collection
        reviews = list(get_collection("reviews").find({"client_id": str(user.id)}))
        profile.total_reviews = len(reviews)
        if reviews:
            profile.avg_rating_given = round(
                sum(r.get("rating", 0) for r in reviews) / len(reviews), 2
            )
    except Exception:
        pass

    # Abandons panier
    profile.cart_abandonments = UserEvent.objects.filter(
        user=user, event_type="cart_abandoned"
    ).count()

    # Scores
    profile.loyalty_tier = profile.compute_loyalty_tier()
    profile.engagement_score = profile.compute_engagement_score()

    # Churn risk : si inactif depuis > 30 jours - risque élevé
    if profile.last_seen_at:
        days_inactive = (timezone.now() - profile.last_seen_at).days
        if days_inactive > 30:
            profile.churn_risk_score = min(100, days_inactive - 30)
        else:
            profile.churn_risk_score = 0
    else:
        profile.churn_risk_score = 0

    profile.save()
    return profile


# STATISTIQUES GLOBALES PLATEFORME

def get_platform_overview(days: int = 30) -> dict:
    """Statistiques globales de la plateforme sur N jours."""
    since = timezone.now() - timedelta(days=days)

    # Sessions
    sessions = UserSession.objects.filter(started_at__gte=since)
    session_stats = sessions.aggregate(
        total=Count("id"),
        unique_users=Count("user", distinct=True),
        avg_duration=Avg("duration_seconds"),
        bounce_count=Count("id", filter=Q(is_bounce=True)),
    )

    # Page views
    pv_stats = PageView.objects.filter(timestamp__gte=since).aggregate(
        total=Count("id"),
        avg_response_ms=Avg("response_time_ms"),
        errors_4xx=Count("id", filter=Q(http_status__gte=400, http_status__lt=500)),
        errors_5xx=Count("id", filter=Q(http_status__gte=500)),
    )

    # Top pages
    top_pages = list(
        PageView.objects.filter(timestamp__gte=since)
        .values("path")
        .annotate(hits=Count("id"), avg_ms=Avg("response_time_ms"))
        .order_by("-hits")[:10]
    )

    # Commandes
    order_stats = Order.objects.filter(created_at__gte=since).aggregate(
        total=Count("id"),
        revenue=Sum("total_price"),
        avg_value=Avg("total_price"),
        cancelled=Count("id", filter=Q(status="cancelled")),
        delivered=Count("id", filter=Q(status="delivered")),
    )

    # Nouveaux utilisateurs
    new_users = User.objects.filter(created_at__gte=since).count()

    # Événements les plus fréquents
    top_events = list(
        UserEvent.objects.filter(timestamp__gte=since)
        .values("event_type")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:10]
    )

    # Taux de conversion
    total_funnels = ConversionFunnel.objects.filter(started_at__gte=since).count()
    converted_funnels = ConversionFunnel.objects.filter(
        started_at__gte=since, converted=True
    ).count()
    conversion_rate = (
        round(converted_funnels / total_funnels * 100, 2)
        if total_funnels > 0 else 0
    )

    # Devices
    device_breakdown = list(
        UserSession.objects.filter(started_at__gte=since)
        .values("device_type")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    # Activité heure par heure (24h glissant)
    last_24h = timezone.now() - timedelta(hours=24)
    hourly_activity = list(
        PageView.objects.filter(timestamp__gte=last_24h)
        .annotate(hour=TruncHour("timestamp"))
        .values("hour")
        .annotate(hits=Count("id"))
        .order_by("hour")
    )

    bounce_rate = (
        round(session_stats["bounce_count"] / session_stats["total"] * 100, 2)
        if session_stats["total"] else 0
    )

    return {
        "period_days": days,
        "sessions": {
            "total": session_stats["total"] or 0,
            "unique_users": session_stats["unique_users"] or 0,
            "avg_duration_seconds": int(session_stats["avg_duration"] or 0),
            "bounce_rate_pct": bounce_rate,
        },
        "page_views": {
            "total": pv_stats["total"] or 0,
            "avg_response_ms": int(pv_stats["avg_response_ms"] or 0),
            "errors_4xx": pv_stats["errors_4xx"] or 0,
            "errors_5xx": pv_stats["errors_5xx"] or 0,
            "top_pages": top_pages,
        },
        "orders": {
            "total": order_stats["total"] or 0,
            "revenue_xaf": float(order_stats["revenue"] or 0),
            "avg_value_xaf": float(order_stats["avg_value"] or 0),
            "cancelled": order_stats["cancelled"] or 0,
            "delivered": order_stats["delivered"] or 0,
        },
        "users": {
            "new": new_users,
            "total": User.objects.count(),
        },
        "conversion": {
            "rate_pct": conversion_rate,
            "funnels_total": total_funnels,
            "funnels_converted": converted_funnels,
        },
        "top_events": top_events,
        "device_breakdown": device_breakdown,
        "hourly_activity_24h": [
            {"hour": h["hour"].isoformat(), "hits": h["hits"]}
            for h in hourly_activity
        ],
    }


def get_user_full_report(user: User) -> dict:
    """
    Rapport complet 360° d'un utilisateur spécifique.
    """
    profile = refresh_user_analytics_profile(user)

    # Historique des sessions
    recent_sessions = list(
        UserSession.objects.filter(user=user)
        .order_by("-started_at")[:20]
        .values(
            "id", "started_at", "ended_at", "duration_seconds",
            "ip_address", "country", "city",
            "device_type", "os", "browser",
            "page_views_count", "events_count", "orders_count",
            "is_bounce", "referrer",
        )
    )

    # Pages les plus visitées
    top_pages = list(
        PageView.objects.filter(user=user)
        .values("path", "method")
        .annotate(
            hits=Count("id"),
            avg_ms=Avg("response_time_ms"),
            last_visit=Max("timestamp"),
        )
        .order_by("-hits")[:20]
    )

    # Derniers événements
    recent_events = list(
        UserEvent.objects.filter(user=user)
        .order_by("-timestamp")[:50]
        .values("event_type", "object_type", "object_id", "properties", "timestamp")
    )

    # Timeline des commandes
    orders_timeline = list(
        Order.objects.filter(client=user)
        .select_related("restaurant")
        .order_by("-created_at")[:20]
        .values(
            "id", "status", "total_price", "created_at",
            "restaurant__name", "delivery_address",
        )
    )

    # Funnel history
    funnel_history = list(
        ConversionFunnel.objects.filter(user=user)
        .order_by("-started_at")[:10]
        .values(
            "restaurant_name", "last_step_name", "converted",
            "order_total", "time_to_convert_seconds",
            "abandoned_at_step", "started_at",
        )
    )

    # Recherches récentes
    recent_searches = list(
        SearchQuery.objects.filter(user=user)
        .order_by("-timestamp")[:20]
        .values("query", "results_count", "timestamp", "filters_applied")
    )

    # Alertes actives
    active_alerts = list(
        BehavioralAlert.objects.filter(user=user, is_resolved=False)
        .values("alert_type", "severity", "message", "created_at")
    )

    # Reviews depuis MongoDB
    reviews = []
    try:
        from core.mongo import get_collection
        raw = list(
            get_collection("reviews").find(
                {"client_id": str(user.id)},
                {"_id": 0}
            ).sort("created_at", -1).limit(10)
        )
        reviews = [
            {**r, "created_at": r["created_at"].isoformat() if hasattr(r.get("created_at"), "isoformat") else str(r.get("created_at", ""))}
            for r in raw
        ]
    except Exception:
        pass

    # Compteurs Redis temps réel
    redis_stats = {}
    try:
        from core.redis_client import get_redis
        r = get_redis()
        redis_stats["driver_available"] = bool(
            r.exists(f"driver:{user.id}:available")
        )
        redis_stats["active_order_count"] = len(r.keys(f"order:*:status"))
    except Exception:
        pass

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at.isoformat(),
        },
        "profile_summary": {
            "loyalty_tier": profile.loyalty_tier,
            "engagement_score": float(profile.engagement_score),
            "churn_risk_score": float(profile.churn_risk_score),
            "total_sessions": profile.total_sessions,
            "total_orders": profile.total_orders,
            "total_spent_xaf": float(profile.total_spent_xaf),
            "avg_order_value_xaf": float(profile.avg_order_value_xaf),
            "first_seen_at": profile.first_seen_at.isoformat() if profile.first_seen_at else None,
            "last_seen_at": profile.last_seen_at.isoformat() if profile.last_seen_at else None,
            "preferred_device": profile.preferred_device,
            "preferred_os": profile.preferred_os,
            "primary_city": profile.primary_city,
            "most_active_hour": profile.most_active_hour,
            "most_active_day": profile.most_active_day,
            "favorite_restaurant": profile.favorite_restaurant_name,
            "cart_abandonments": profile.cart_abandonments,
            "total_reviews": profile.total_reviews,
            "avg_rating_given": float(profile.avg_rating_given),
        },
        "sessions": recent_sessions,
        "top_visited_pages": top_pages,
        "recent_events": recent_events,
        "orders_timeline": orders_timeline,
        "funnel_history": funnel_history,
        "recent_searches": recent_searches,
        "reviews": reviews,
        "active_alerts": active_alerts,
        "redis_live": redis_stats,
        "behavioral_patterns": {
            "orders_by_hour": profile.orders_by_hour,
            "orders_by_day": profile.orders_by_day,
            "top_search_queries": profile.top_search_queries,
            "top_visited_paths": profile.top_visited_paths,
            "known_ips": profile.known_ips,
        },
    }


def get_funnel_analysis(days: int = 30) -> dict:
    """Analyse détaillée du funnel de conversion sur N jours."""
    since = timezone.now() - timedelta(days=days)
    funnels = ConversionFunnel.objects.filter(started_at__gte=since)

    total = funnels.count()
    if total == 0:
        return {"message": "Aucun funnel sur cette période", "period_days": days}

    step_counts = {}
    for step_num, step_name in ConversionFunnel.STEP_CHOICES:
        step_counts[step_name] = funnels.filter(last_step__gte=step_num).count()

    converted = funnels.filter(converted=True)
    abandoned = funnels.filter(converted=False)

    abandon_by_step = dict(
        abandoned.values("abandoned_at_step")
        .annotate(cnt=Count("id"))
        .values_list("abandoned_at_step", "cnt")
    )

    avg_convert_time = converted.aggregate(avg=Avg("time_to_convert_seconds"))["avg"]

    top_abandoned_restaurants = list(
        abandoned.exclude(restaurant_name="")
        .values("restaurant_name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:5]
    )

    return {
        "period_days": days,
        "total_funnels": total,
        "conversion_rate_pct": round(converted.count() / total * 100, 2),
        "avg_time_to_convert_seconds": int(avg_convert_time or 0),
        "funnel_steps": [
            {
                "step": step_name,
                "users_reached": step_counts.get(step_name, 0),
                "drop_off_pct": round(
                    (1 - step_counts.get(step_name, 0) / total) * 100, 2
                ) if total else 0,
            }
            for _, step_name in ConversionFunnel.STEP_CHOICES
        ],
        "abandon_by_step": abandon_by_step,
        "top_abandoned_restaurants": top_abandoned_restaurants,
    }


def detect_behavioral_anomalies():
    """
    Détecte automatiquement les anomalies comportementales et lève des alertes.
    À appeler périodiquement (cron, celery beat).
    """
    from analytics.tracker import raise_alert
    alerts_raised = 0

    # Utilisateurs inactifs depuis 30 jours
    threshold_inactive = timezone.now() - timedelta(days=30)
    inactive_users = User.objects.filter(
        analytics_profile__last_seen_at__lt=threshold_inactive,
        analytics_profile__churn_risk_score=0,
    )
    for user in inactive_users[:100]:
        raise_alert(
            user, "inactive_user",
            f"Utilisateur inactif depuis plus de 30 jours",
            severity="warning",
            details={"last_seen": str(user.analytics_profile.last_seen_at)},
        )
        alerts_raised += 1

    # Taux d'annulation élevé
    high_cancel_users = (
        Order.objects.filter(status="cancelled")
        .values("client")
        .annotate(cancel_cnt=Count("id"), total_cnt=Count("id"))
        .filter(cancel_cnt__gte=3)
    )
    for entry in high_cancel_users:
        try:
            user = User.objects.get(pk=entry["client"])
            raise_alert(
                user, "high_cancellation_rate",
                f"{entry['cancel_cnt']} commandes annulées",
                severity="warning",
                details={"cancel_count": entry["cancel_cnt"]},
            )
            alerts_raised += 1
        except User.DoesNotExist:
            pass

    # Plusieurs paiements échoués
    failed_payment_users = (
        UserEvent.objects.filter(event_type="payment_failed")
        .values("user")
        .annotate(cnt=Count("id"))
        .filter(cnt__gte=3)
    )
    for entry in failed_payment_users:
        if not entry["user"]:
            continue
        try:
            user = User.objects.get(pk=entry["user"])
            raise_alert(
                user, "multiple_failed_payments",
                f"{entry['cnt']} tentatives de paiement échouées",
                severity="critical",
                details={"failed_count": entry["cnt"]},
            )
            alerts_raised += 1
        except User.DoesNotExist:
            pass

    logger.info(f"detect_behavioral_anomalies: {alerts_raised} alertes levées")
    return alerts_raised


# MISE À JOUR DU PROFIL DE GOÛTS (ItemInteraction - UserTasteProfile)

def refresh_taste_profile(user: User):
    """
    Recalcule le UserTasteProfile à partir de toutes les ItemInteraction.
    POSTGRES : agrégations sur item_interactions - COUNT, SUM, GROUP BY.
    Appelé par signal après chaque nouvelle interaction.
    """
    from .models import ItemInteraction, UserTasteProfile
    from collections import defaultdict
    from decimal import Decimal

    profile, _ = UserTasteProfile.objects.get_or_create(user=user)

    interactions = ItemInteraction.objects.filter(user=user)
    total = interactions.count()
    total_score = interactions.aggregate(s=Sum("weight"))["s"] or 0

    profile.total_interactions = total
    profile.total_score = total_score

    # Score par item
    item_scores = defaultdict(int)
    item_names = {}
    for inter in interactions.values("item_id", "item_name", "weight"):
        item_scores[inter["item_id"]] += inter["weight"]
        item_names[inter["item_id"]] = inter["item_name"]

    # Top items positifs
    profile.top_item_ids = [
        item_id for item_id, score in
        sorted(item_scores.items(), key=lambda x: -x[1])
        if score > 0
    ][:20]

    # Items évités (score négatif)
    profile.avoided_item_ids = [
        item_id for item_id, score in item_scores.items()
        if score < 0
    ][:10]

    # Score par tag
    tag_scores = defaultdict(int)
    for inter in interactions.values("item_tags", "weight"):
        for tag in (inter["item_tags"] or []):
            tag_scores[tag] += inter["weight"]

    profile.favorite_tags = [
        {"tag": tag, "score": score}
        for tag, score in sorted(tag_scores.items(), key=lambda x: -x[1])
        if score > 0
    ][:15]

    # Score par restaurant
    restaurant_scores = defaultdict(int)
    for inter in interactions.values("restaurant_id", "weight"):
        restaurant_scores[str(inter["restaurant_id"])] += inter["weight"]
    profile.restaurant_scores = dict(restaurant_scores)

    # Analyse des prix
    prices_qs = interactions.filter(
        item_price__isnull=False,
        interaction_type__in=["ordered", "added_to_cart"]
    ).values_list("item_price", flat=True)
    prices = [float(p) for p in prices_qs]
    if prices:
        profile.avg_item_price = Decimal(str(round(sum(prices) / len(prices), 2)))
        profile.max_comfortable_price = Decimal(str(sorted(prices)[-1]))

    # Options fréquentes
    option_counter = defaultdict(int)
    for inter in interactions.filter(
        interaction_type__in=["ordered", "added_to_cart"]
    ).values("selected_options"):
        for opt in (inter["selected_options"] or []):
            label = opt.get("label", "")
            if label:
                option_counter[label] += 1
    profile.frequent_options = [
        {"label": label, "frequency": cnt}
        for label, cnt in sorted(option_counter.items(), key=lambda x: -x[1])
    ][:10]

    profile.save()
    return profile


# STATISTIQUES ANALYTIQUES CART + RATINGS

def get_cart_analytics(days: int = 30) -> dict:
    """
    Statistiques d'abandon de panier et de conversion.
    POSTGRES : agrégations sur CartSession.
    """
    from cart.models import CartSession, ItemRating, RestaurantRating

    since = timezone.now() - timedelta(days=days)
    sessions = CartSession.objects.filter(created_at__gte=since)

    agg = sessions.aggregate(
        total=Count("id"),
        converted=Count("id", filter=Q(status="converted")),
        abandoned=Count("id", filter=Q(status="abandoned")),
        active=Count("id", filter=Q(status="active")),
        avg_subtotal=Avg("subtotal"),
        avg_items=Avg("items_count"),
    )

    conversion_rate = (
        round(agg["converted"] / agg["total"] * 100, 2)
        if agg["total"] else 0
    )

    # Top restaurants par paniers ouverts
    top_restaurants = list(
        sessions.values("restaurant__name")
        .annotate(cnt=Count("id"), converted=Count("id", filter=Q(status="converted")))
        .order_by("-cnt")[:10]
    )

    # Statistiques de notation
    rating_stats = ItemRating.objects.filter(created_at__gte=since).aggregate(
        total=Count("id"),
        avg=Avg("rating"),
        five_star=Count("id", filter=Q(rating=5)),
        four_star=Count("id", filter=Q(rating=4)),
        three_star=Count("id", filter=Q(rating=3)),
        two_star=Count("id", filter=Q(rating=2)),
        one_star=Count("id", filter=Q(rating=1)),
    )

    # Top plats les mieux notés
    top_rated_items = list(
        ItemRating.objects.filter(created_at__gte=since)
        .values("item_name", "item_id")
        .annotate(avg_r=Avg("rating"), cnt=Count("id"))
        .filter(cnt__gte=2)
        .order_by("-avg_r")[:10]
    )

    # Top restaurants par note
    top_rated_restaurants = list(
        RestaurantRating.objects.select_related("restaurant")
        .order_by("-avg_rating")
        .values("restaurant__name", "avg_rating", "total_ratings")[:10]
    )

    return {
        "period_days": days,
        "cart_sessions": {
            "total": agg["total"] or 0,
            "converted": agg["converted"] or 0,
            "abandoned": agg["abandoned"] or 0,
            "active": agg["active"] or 0,
            "conversion_rate_pct": conversion_rate,
            "avg_subtotal_xaf": float(agg["avg_subtotal"] or 0),
            "avg_items_per_cart": round(float(agg["avg_items"] or 0), 2),
        },
        "top_restaurants_by_cart": top_restaurants,
        "ratings": {
            "total": rating_stats["total"] or 0,
            "avg_rating": round(float(rating_stats["avg"] or 0), 2),
            "distribution": {
                "5": rating_stats["five_star"] or 0,
                "4": rating_stats["four_star"] or 0,
                "3": rating_stats["three_star"] or 0,
                "2": rating_stats["two_star"] or 0,
                "1": rating_stats["one_star"] or 0,
            },
        },
        "top_rated_items": top_rated_items,
        "top_rated_restaurants": top_rated_restaurants,
    }


def get_item_interaction_analysis(days: int = 30) -> dict:
    """
    Analyse des interactions avec les plats pour le moteur de recommandation.
    """
    from .models import ItemInteraction

    since = timezone.now() - timedelta(days=days)
    interactions = ItemInteraction.objects.filter(timestamp__gte=since)

    # Par type d'interaction
    by_type = dict(
        interactions.values("interaction_type")
        .annotate(cnt=Count("id"))
        .values_list("interaction_type", "cnt")
    )

    # Plats les plus interagis
    top_items = list(
        interactions.values("item_id", "item_name")
        .annotate(
            total_interactions=Count("id"),
            total_score=Sum("weight"),
            add_to_cart=Count("id", filter=Q(interaction_type="added_to_cart")),
            ordered=Count("id", filter=Q(interaction_type="ordered")),
        )
        .order_by("-total_score")[:15]
    )

    # Tags les plus populaires
    tag_counter = defaultdict(int)
    for inter in interactions.values("item_tags", "weight"):
        for tag in (inter["item_tags"] or []):
            tag_counter[tag] += inter["weight"]
    top_tags = sorted(tag_counter.items(), key=lambda x: -x[1])[:15]

    # Options les plus choisies
    option_counter = defaultdict(int)
    for inter in interactions.filter(
        interaction_type__in=["ordered", "added_to_cart"]
    ).values("selected_options"):
        for opt in (inter["selected_options"] or []):
            label = opt.get("label", "")
            if label:
                option_counter[label] += 1
    top_options = sorted(option_counter.items(), key=lambda x: -x[1])[:10]

    return {
        "period_days": days,
        "total_interactions": interactions.count(),
        "by_type": by_type,
        "top_items": top_items,
        "top_tags": [{"tag": t, "score": s} for t, s in top_tags],
        "top_chosen_options": [{"label": l, "count": c} for l, c in top_options],
    }


from collections import defaultdict
