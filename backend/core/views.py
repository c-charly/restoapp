"""
Page d'accueil avec recommandations personnalisées.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .recommendations import get_homepage_feed, track_item_view


class HomepageFeedView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["homepage"],
        summary="Page d'accueil - Feed personnalisé",
        description=(
            "**Moteur de recommandation** :\n\n"
            "- **Utilisateur authentifié avec historique** - Recommandations basées sur :\n"
            "  - Tags des plats commandés (goûts détectés)\n"
            "  - Restaurant favori - nouvelles découvertes\n"
            "  - Plats >= 4 étoiles dans ses restaurants connus\n"
            "- **Nouvel utilisateur** - Top global\n"
            "- **Anonyme** - Top plats notés sur la plateforme\n\n"
        ),
        parameters=[
            OpenApiParameter("lat", OpenApiTypes.FLOAT, description="Latitude (géoloc optionnelle)", required=False),
            OpenApiParameter("lng", OpenApiTypes.FLOAT, description="Longitude (géoloc optionnelle)", required=False),
            OpenApiParameter("limit", OpenApiTypes.INT, description="Nombre d'items (défaut: 20)", required=False),
        ],
    )
    def get(self, request):
        user = request.user if request.user.is_authenticated else None

        try:
            lat = float(request.query_params.get("lat")) if request.query_params.get("lat") else None
            lng = float(request.query_params.get("lng")) if request.query_params.get("lng") else None
            limit = min(int(request.query_params.get("limit", 20)), 50)
        except (TypeError, ValueError):
            lat, lng, limit = None, None, 20

        feed = get_homepage_feed(user=user, lat=lat, lng=lng, limit=limit)
        return Response(feed)

    @extend_schema(
        tags=["homepage"],
        summary="Tracker la vue d'un item",
        description=(
            "Enregistre qu'un utilisateur a vu un item. "
            "Incrémente le compteur Redis pour le calcul trending. "
            "Logge l'événement analytique."
        ),
    )
    def post(self, request):
        item_id = request.data.get("item_id")
        restaurant_id = request.data.get("restaurant_id")
        if not item_id or not restaurant_id:
            return Response({"error": "item_id et restaurant_id requis."}, status=400)

        user_id = str(request.user.id) if request.user.is_authenticated else "anonymous"

        # REDIS : incrémente le compteur trending
        track_item_view(user_id, item_id, restaurant_id)

        # Analytique
        if request.user.is_authenticated:
            try:
                from analytics.models import UserEvent
                UserEvent.objects.create(
                    user=request.user,
                    event_type="item_viewed",
                    object_type="menu_item",
                    object_id=item_id,
                    properties={
                        "restaurant_id": restaurant_id,
                        "item_id": item_id,
                    },
                )
            except Exception:
                pass

        return Response({"tracked": True, "item_id": item_id})
