"""
Endpoints analytiques - tableau de bord complet plateforme + par utilisateur.

Tous les endpoints sont réservés aux admins sauf :
- /analytics/me/       - utilisateur connecté (son propre profil)
- /analytics/track/    - frontend (tracking événements)
"""
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Avg, Sum, Q, Max

from accounts.models import User
from orders.models import Order
from .models import (
    UserSession, PageView, UserEvent,
    UserAnalyticsProfile, ConversionFunnel,
    SearchQuery, BehavioralAlert,
)
from .serializers import (
    UserSessionSerializer, PageViewSerializer, UserEventSerializer,
    UserAnalyticsProfileSerializer, BehavioralAlertSerializer,
    ConversionFunnelSerializer, TrackEventSerializer, TrackSearchSerializer,
)
from .services import (
    get_platform_overview, get_user_full_report,
    refresh_user_analytics_profile, get_funnel_analysis,
    detect_behavioral_anomalies,
)
from .tracker import track, track_search


# TRACKING (frontend - backend)

class TrackEventView(APIView):
    """Endpoint appelé par le frontend pour tracker un événement."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["analytics"],
        summary="Tracker un événement comportemental",
        description="Enregistre un événement depuis le frontend (mobile ou web).",
        request=TrackEventSerializer,
    )
    def post(self, request):
        serializer = TrackEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        event = track(
            request,
            event_type=serializer.validated_data["event_type"],
            object_type=serializer.validated_data.get("object_type", ""),
            object_id=serializer.validated_data.get("object_id", ""),
            properties=serializer.validated_data.get("properties", {}),
        )
        return Response({"tracked": True, "event_id": str(event.id) if event else None})


class TrackSearchView(APIView):
    """Endpoint pour tracker une recherche utilisateur."""
    permission_classes = [AllowAny]

    @extend_schema(tags=["analytics"], summary="Tracker une recherche")
    def post(self, request):
        serializer = TrackSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        track_search(
            request,
            query=serializer.validated_data["query"],
            results_count=serializer.validated_data.get("results_count", 0),
            filters=serializer.validated_data.get("filters", {}),
        )
        return Response({"tracked": True})


# MON PROFIL ANALYTIQUE (utilisateur connecté)

class MyAnalyticsView(APIView):
    """L'utilisateur connecté consulte ses propres statistiques."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["analytics"],
        summary="Mon profil analytique personnel",
        description=(
            "Retourne vos statistiques personnelles : sessions, commandes, "
            "habitudes, pages visitées, fidélité, score d'engagement."
        ),
    )
    def get(self, request):
        profile = refresh_user_analytics_profile(request.user)
        return Response(UserAnalyticsProfileSerializer(profile).data)


class MySessionsView(ListAPIView):
    """Historique des sessions de l'utilisateur connecté."""
    serializer_class = UserSessionSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["analytics"], summary="Mes sessions de connexion")
    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user).order_by("-started_at")[:50]


class MyEventsView(ListAPIView):
    """Historique des événements de l'utilisateur connecté."""
    serializer_class = UserEventSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["analytics"], summary="Mon historique d'actions")
    def get_queryset(self):
        return UserEvent.objects.filter(user=self.request.user).order_by("-timestamp")[:100]


# TABLEAU DE BORD PLATEFORME (admin)

class PlatformOverviewView(APIView):
    """Vue d'ensemble globale de la plateforme - admin uniquement."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Vue d'ensemble plateforme",
        description=(
            "Statistiques globales : sessions, page views, commandes, revenus, "
            "taux de conversion, device breakdown, activité horaire."
        ),
        parameters=[
            OpenApiParameter("days", OpenApiTypes.INT, description="Fenêtre en jours (défaut: 30)", required=False),
        ],
    )
    def get(self, request):
        days = int(request.query_params.get("days", 30))
        days = max(1, min(days, 365))
        return Response(get_platform_overview(days))


class PlatformRealTimeView(APIView):
    """Statistiques temps réel depuis Redis - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Stats temps réel (Redis)",
        description="Compteurs d'événements en temps réel depuis Redis (dernières 24h).",
    )
    def get(self, request):
        from core.redis_client import get_redis
        from datetime import datetime, timezone
        r = get_redis()

        # Lire tous les compteurs horaires des 24 dernières heures
        now = datetime.now(timezone.utc)
        event_types = [
            "page_view", "order_confirmed", "payment_success", "payment_failed",
            "search", "login", "register", "cart_abandoned",
        ]

        realtime_data = {}
        for event_type in event_types:
            total = 0
            hourly = {}
            for h in range(24):
                ts = now - timedelta(hours=h)
                key = f"analytics:events:{event_type}:{ts.strftime('%Y%m%d%H')}"
                try:
                    val = int(r.get(key) or 0)
                    total += val
                    hourly[ts.strftime("%H:00")] = val
                except Exception:
                    pass
            realtime_data[event_type] = {"total_24h": total, "by_hour": hourly}

        # Livreurs actifs
        try:
            driver_keys = r.keys("driver:*:available")
            active_drivers = len(driver_keys)
        except Exception:
            active_drivers = 0

        # Commandes en cours
        try:
            order_statuses = r.keys("order:*:status")
            active_orders = len(order_statuses)
        except Exception:
            active_orders = 0

        return Response({
            "source": "Redis - temps réel",
            "active_drivers": active_drivers,
            "active_orders_in_cache": active_orders,
            "event_counters_24h": realtime_data,
        })


class UserListAnalyticsView(APIView):
    """Liste de tous les utilisateurs avec leur profil analytique - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Tous les utilisateurs + profil analytique",
        description="Liste paginée avec scores d'engagement, fidélité, risque de départ.",
        parameters=[
            OpenApiParameter("role", OpenApiTypes.STR, required=False),
            OpenApiParameter("loyalty_tier", OpenApiTypes.STR, required=False),
            OpenApiParameter("min_engagement", OpenApiTypes.FLOAT, required=False),
            OpenApiParameter("churn_risk", OpenApiTypes.BOOL, required=False),
            OpenApiParameter("order_by", OpenApiTypes.STR, required=False,
                            description="engagement_score | churn_risk_score | total_spent_xaf | last_seen_at"),
        ],
    )
    def get(self, request):
        qs = User.objects.prefetch_related("analytics_profile").all()

        # Filtres
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)

        loyalty_tier = request.query_params.get("loyalty_tier")
        if loyalty_tier:
            qs = qs.filter(analytics_profile__loyalty_tier=loyalty_tier)

        min_engagement = request.query_params.get("min_engagement")
        if min_engagement:
            qs = qs.filter(analytics_profile__engagement_score__gte=float(min_engagement))

        churn_risk = request.query_params.get("churn_risk")
        if churn_risk and churn_risk.lower() == "true":
            qs = qs.filter(analytics_profile__churn_risk_score__gte=50)

        # Tri
        order_by = request.query_params.get("order_by", "-analytics_profile__engagement_score")
        valid_sorts = [
            "analytics_profile__engagement_score", "-analytics_profile__engagement_score",
            "analytics_profile__churn_risk_score", "-analytics_profile__churn_risk_score",
            "analytics_profile__total_spent_xaf", "-analytics_profile__total_spent_xaf",
            "analytics_profile__last_seen_at", "-analytics_profile__last_seen_at",
        ]
        if order_by not in valid_sorts:
            order_by = "-analytics_profile__engagement_score"

        try:
            qs = qs.order_by(order_by)
        except Exception:
            pass

        users_data = []
        for user in qs[:200]:
            try:
                p = user.analytics_profile
                users_data.append({
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat(),
                    "loyalty_tier": p.loyalty_tier,
                    "engagement_score": float(p.engagement_score),
                    "churn_risk_score": float(p.churn_risk_score),
                    "total_orders": p.total_orders,
                    "total_spent_xaf": float(p.total_spent_xaf),
                    "last_seen_at": p.last_seen_at.isoformat() if p.last_seen_at else None,
                    "preferred_device": p.preferred_device,
                    "primary_city": p.primary_city,
                })
            except UserAnalyticsProfile.DoesNotExist:
                users_data.append({
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
                    "created_at": user.created_at.isoformat(),
                    "profile": "non calculé",
                })

        return Response({"count": len(users_data), "users": users_data})


class UserDetailAnalyticsView(APIView):
    """Rapport 360° complet d'un utilisateur spécifique - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Rapport 360° d'un utilisateur",
        description=(
            "Rapport complet : sessions, pages visitées, événements, commandes, "
            "funnel, recherches, reviews, alertes, patterns comportementaux.\n\n"
            "**Sources** : PostgreSQL + MongoDB (reviews) + Redis (live data)."
        ),
    )
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable"}, status=404)

        return Response(get_user_full_report(user))


class UserSessionsAdminView(ListAPIView):
    """Sessions d'un utilisateur spécifique - admin."""
    serializer_class = UserSessionSerializer
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["analytics-admin"], summary="Sessions d'un utilisateur")
    def get_queryset(self):
        return UserSession.objects.filter(
            user_id=self.kwargs["user_id"]
        ).order_by("-started_at")


class UserEventsAdminView(ListAPIView):
    """Événements d'un utilisateur spécifique - admin."""
    serializer_class = UserEventSerializer
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["analytics-admin"], summary="Événements d'un utilisateur")
    def get_queryset(self):
        return UserEvent.objects.filter(
            user_id=self.kwargs["user_id"]
        ).order_by("-timestamp")


# PAGES / ENDPOINTS LES PLUS VISITES

class TopPagesView(APIView):
    """Pages les plus visitées sur la plateforme - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Pages / endpoints les plus visités",
        parameters=[
            OpenApiParameter("days", OpenApiTypes.INT, required=False),
            OpenApiParameter("method", OpenApiTypes.STR, required=False),
        ],
    )
    def get(self, request):
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)
        qs = PageView.objects.filter(timestamp__gte=since)

        method = request.query_params.get("method")
        if method:
            qs = qs.filter(method=method.upper())

        pages = list(
            qs.values("path", "method")
            .annotate(
                hits=Count("id"),
                unique_users=Count("user", distinct=True),
                avg_response_ms=Avg("response_time_ms"),
                errors=Count("id", filter=Q(http_status__gte=400)),
                last_accessed=Max("timestamp"),
            )
            .order_by("-hits")[:50]
        )

        # Erreurs les plus fréquentes
        errors = list(
            qs.filter(http_status__gte=400)
            .values("path", "http_status")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:20]
        )

        # Réponses les plus lentes
        slowest = list(
            qs.values("path")
            .annotate(avg_ms=Avg("response_time_ms"))
            .order_by("-avg_ms")[:10]
        )

        return Response({
            "period_days": days,
            "top_pages": pages,
            "frequent_errors": errors,
            "slowest_endpoints": slowest,
        })


# FUNNEL DE CONVERSION

class FunnelAnalysisView(APIView):
    """Analyse du funnel de conversion - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Funnel de conversion",
        description="Taux de conversion étape par étape, points d'abandon, temps de conversion.",
        parameters=[
            OpenApiParameter("days", OpenApiTypes.INT, required=False),
        ],
    )
    def get(self, request):
        days = int(request.query_params.get("days", 30))
        return Response(get_funnel_analysis(days))


# ALERTES COMPORTEMENTALES

class BehavioralAlertsView(APIView):
    """Liste des alertes comportementales actives - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Alertes comportementales",
        parameters=[
            OpenApiParameter("severity", OpenApiTypes.STR, required=False),
            OpenApiParameter("alert_type", OpenApiTypes.STR, required=False),
        ],
    )
    def get(self, request):
        qs = BehavioralAlert.objects.filter(is_resolved=False).select_related("user")

        severity = request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)

        alert_type = request.query_params.get("alert_type")
        if alert_type:
            qs = qs.filter(alert_type=alert_type)

        alerts = BehavioralAlertSerializer(qs.order_by("-created_at")[:100], many=True).data
        return Response({
            "total_unresolved": qs.count(),
            "alerts": alerts,
        })

    @extend_schema(
        tags=["analytics-admin"],
        summary="Lancer la détection automatique d'anomalies",
    )
    def post(self, request):
        """Déclenche manuellement la détection d'anomalies."""
        count = detect_behavioral_anomalies()
        return Response({"alerts_raised": count})


class ResolveAlertView(APIView):
    """Marquer une alerte comme résolue - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(tags=["analytics-admin"], summary="Résoudre une alerte")
    def patch(self, request, alert_id):
        try:
            alert = BehavioralAlert.objects.get(id=alert_id)
            alert.is_resolved = True
            alert.resolved_at = timezone.now()
            alert.save(update_fields=["is_resolved", "resolved_at"])
            return Response({"resolved": True})
        except BehavioralAlert.DoesNotExist:
            return Response({"error": "Alerte introuvable"}, status=404)


# RECHERCHES PLATEFORME

class TopSearchesView(APIView):
    """Termes les plus recherchés - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Top recherches plateforme",
        parameters=[
            OpenApiParameter("days", OpenApiTypes.INT, required=False),
        ],
    )
    def get(self, request):
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)

        top = list(
            SearchQuery.objects.filter(timestamp__gte=since)
            .values("query_normalized")
            .annotate(
                cnt=Count("id"),
                avg_results=Avg("results_count"),
                zero_results=Count("id", filter=Q(results_count=0)),
            )
            .order_by("-cnt")[:30]
        )

        # Recherches sans résultat (lacunes de catalogue)
        no_results = list(
            SearchQuery.objects.filter(timestamp__gte=since, results_count=0)
            .values("query_normalized")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:15]
        )

        return Response({
            "period_days": days,
            "top_searches": top,
            "searches_with_no_results": no_results,
        })


# SEGMENTATION UTILISATEURS

class UserSegmentationView(APIView):
    """Segmentation automatique des utilisateurs par comportement - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Segmentation utilisateurs",
        description=(
            "Répartition par tier de fidélité, device, ville, "
            "score d'engagement et risque de départ."
        ),
    )
    def get(self, request):
        profiles = UserAnalyticsProfile.objects.all()

        # Répartition par tier
        by_tier = dict(
            profiles.values("loyalty_tier")
            .annotate(cnt=Count("id"))
            .values_list("loyalty_tier", "cnt")
        )

        # Répartition par device
        by_device = dict(
            profiles.exclude(preferred_device="")
            .values("preferred_device")
            .annotate(cnt=Count("id"))
            .values_list("preferred_device", "cnt")
        )

        # Répartition par ville
        by_city = list(
            profiles.exclude(primary_city="")
            .values("primary_city")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:10]
        )

        # Utilisateurs à haut risque de départ
        churn_risk_users = profiles.filter(churn_risk_score__gte=50).count()
        total_users = profiles.count()

        # Distribution des scores d'engagement
        engagement_dist = {
            "0-25 (faible)": profiles.filter(engagement_score__lte=25).count(),
            "26-50 (moyen)": profiles.filter(engagement_score__gt=25, engagement_score__lte=50).count(),
            "51-75 (bon)": profiles.filter(engagement_score__gt=50, engagement_score__lte=75).count(),
            "76-100 (excellent)": profiles.filter(engagement_score__gt=75).count(),
        }

        # Top dépensiers
        top_spenders = list(
            profiles.order_by("-total_spent_xaf")[:10]
            .values("user__email", "total_spent_xaf", "total_orders", "loyalty_tier")
        )

        # Utilisateurs dormants (actifs > 30j)
        dormant_threshold = timezone.now() - timedelta(days=30)
        dormant = profiles.filter(
            last_seen_at__lt=dormant_threshold
        ).count()

        return Response({
            "total_profiles": total_users,
            "by_loyalty_tier": by_tier,
            "by_device": by_device,
            "by_city": by_city,
            "engagement_distribution": engagement_dist,
            "churn_risk": {
                "count": churn_risk_users,
                "pct": round(churn_risk_users / total_users * 100, 2) if total_users else 0,
            },
            "dormant_users_30d": dormant,
            "top_spenders": top_spenders,
        })


# CART ANALYTICS (admin)

class RecordItemInteractionView(APIView):
    """Enregistre une interaction utilisateur avec un item (pour le moteur de reco)."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["analytics"],
        summary="Enregistrer une interaction avec un plat",
        description=(
            "Trace l'interaction d'un utilisateur avec un plat du menu.\n\n"
            "Types : `viewed`, `detail_opened`, `added_to_cart`, `removed_from_cart`, "
            "`ordered`, `rated_positive`, `rated_negative`, `shared`.\n\n"
            "Chaque interaction est **pondérée** (viewed=1, ordered=10, etc.) "
            "et alimente le **profil de goûts** qui personnalise le feed d'accueil."
        ),
    )
    def post(self, request):
        from analytics.models import ItemInteraction
        data = request.data

        required = ["item_id", "item_name", "restaurant_id", "interaction_type"]
        for field in required:
            if not data.get(field):
                return Response({"error": f"{field} requis."}, status=400)

        valid_types = dict(ItemInteraction.INTERACTION_TYPES).keys()
        if data["interaction_type"] not in valid_types:
            return Response({"error": f"Type invalide. Valeurs: {list(valid_types)}"}, status=400)

        interaction = ItemInteraction.objects.create(
            user=request.user,
            item_id=data["item_id"],
            item_name=data["item_name"],
            restaurant_id=data["restaurant_id"],
            interaction_type=data["interaction_type"],
            item_tags=data.get("item_tags", []),
            item_price=data.get("item_price"),
            selected_options=data.get("selected_options", []),
        )
        return Response({
            "recorded": True,
            "interaction_id": str(interaction.id),
            "weight": interaction.weight,
        })


class MyTasteProfileView(APIView):
    """Retourne le profil de gouts de l'utilisateur connecté."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["analytics"],
        summary="Mon profil de goûts (moteur de recommandation)",
        description=(
            "Retourne le profil de goûts calculé depuis toutes les interactions "
            "de l'utilisateur avec les plats :\n\n"
            "- Tags préférés avec scores\n"
            "- Items favoris / évités\n"
            "- Restaurants par affinité\n"
            "- Options fréquemment choisies\n"
            "- Tranche de prix confortable\n\n"
            "Ce profil alimente directement le **feed personnalisé** de la page d'accueil."
        ),
    )
    def get(self, request):
        from analytics.models import UserTasteProfile
        try:
            profile = request.user.taste_profile
            return Response({
                "user_email": request.user.email,
                "favorite_tags": profile.favorite_tags,
                "top_item_ids": profile.top_item_ids,
                "avoided_item_ids": profile.avoided_item_ids,
                "restaurant_scores": profile.restaurant_scores,
                "avg_item_price": float(profile.avg_item_price) if profile.avg_item_price else None,
                "max_comfortable_price": float(profile.max_comfortable_price) if profile.max_comfortable_price else None,
                "frequent_options": profile.frequent_options,
                "total_interactions": profile.total_interactions,
                "updated_at": profile.updated_at.isoformat(),
            })
        except Exception:
            return Response({"message": "Pas encore de profil de goûts. Interagissez avec des plats."})


class ItemInteractionHistoryView(APIView):
    """Historique des interactions avec les items - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="📱 Interactions items d'un utilisateur",
        description=(
            "Historique détaillé de toutes les interactions d'un utilisateur avec les plats. "
            "Utilisé pour auditer le moteur de recommandation."
        ),
    )
    def get(self, request, user_id):
        from analytics.models import ItemInteraction
        interactions = ItemInteraction.objects.filter(
            user_id=user_id
        ).order_by("-timestamp")[:100]

        data = list(interactions.values(
            "item_id", "item_name", "restaurant_id",
            "interaction_type", "weight", "item_tags",
            "item_price", "selected_options", "timestamp",
        ))
        return Response({"count": len(data), "interactions": data})


class GlobalItemInteractionsView(APIView):
    """Stats globales des interactions avec les items - admin."""
    permission_classes = [IsAdminUser]

    @extend_schema(
        tags=["analytics-admin"],
        summary="Stats globales interactions plats",
        description=(
            "Top plats par interaction type, distribution des tags, "
            "options les plus choisies sur la plateforme."
        ),
        parameters=[
            OpenApiParameter("days", OpenApiTypes.INT, required=False),
        ],
    )
    def get(self, request):
        from analytics.models import ItemInteraction

        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)
        qs = ItemInteraction.objects.filter(timestamp__gte=since)

        # Top items commandés
        top_ordered = list(
            qs.filter(interaction_type="ordered")
            .values("item_id", "item_name")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:15]
        )

        # Top items vus
        top_viewed = list(
            qs.filter(interaction_type="viewed")
            .values("item_id", "item_name")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")[:15]
        )

        # Items les plus ajoutés au panier sans commander (friction)
        cart_adds = dict(
            qs.filter(interaction_type="added_to_cart")
            .values("item_id")
            .annotate(cnt=Count("id"))
            .values_list("item_id", "cnt")
        )
        ordered_ids = set(
            qs.filter(interaction_type="ordered")
            .values_list("item_id", flat=True)
        )
        high_friction = [
            {"item_id": iid, "cart_adds": cnt}
            for iid, cnt in sorted(cart_adds.items(), key=lambda x: -x[1])
            if iid not in ordered_ids
        ][:10]

        # Tags les plus interagis
        from collections import Counter
        tag_counter = Counter()
        for row in qs.filter(interaction_type="ordered").values("item_tags")[:500]:
            tag_counter.update(row["item_tags"])
        top_tags = [{"tag": t, "count": c} for t, c in tag_counter.most_common(15)]

        # Options les plus choisies
        opt_counter = Counter()
        for row in qs.filter(interaction_type="added_to_cart").values("selected_options")[:500]:
            for opt in row["selected_options"]:
                if opt.get("label"):
                    opt_counter[opt["label"]] += 1
        top_options = [{"option": o, "count": c} for o, c in opt_counter.most_common(10)]

        return Response({
            "period_days": days,
            "top_ordered_items": top_ordered,
            "top_viewed_items": top_viewed,
            "high_friction_items": high_friction,
            "top_tags": top_tags,
            "top_options_chosen": top_options,
            "total_interactions": qs.count(),
        })
