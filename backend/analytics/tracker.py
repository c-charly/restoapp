"""
API publique de tracking — à appeler depuis n'importe quel service/vue.

Usage :
    from analytics.tracker import track

    track(request, "item_added_to_cart", object_type="menu_item", object_id=item_id,
          properties={"name": "Poulet DG", "price": 3500, "restaurant_id": str(r_id)})

POSTGRES : tous les événements sont liés à des sessions et users par FK.
MONGODB  : les événements sont aussi loggés dans activity_logs pour l'historique brut.
REDIS    : les compteurs temps réel (événements/min) sont incrémentés dans Redis.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger("analytics.tracker")


def track(
    request,
    event_type: str,
    object_type: str = "",
    object_id: str = "",
    properties: dict = None,
    user=None,
):
    """
    Enregistre un événement comportemental.

    Args:
        request     : HttpRequest Django (pour extraire session/IP/user)
        event_type  : type d'événement (voir UserEvent.EVENT_TYPES)
        object_type : type d'objet concerné ('restaurant', 'order', 'menu_item', ...)
        object_id   : identifiant de l'objet
        properties  : dict libre de données contextuelles
        user        : forcer un user différent de request.user
    """
    try:
        from analytics.models import UserEvent, UserSession

        resolved_user = user or (
            request.user if (hasattr(request, "user") and request.user.is_authenticated) else None
        )

        # Récupérer la session analytique depuis le cookie
        session = None
        session_key = request.COOKIES.get("analytics_session")
        if session_key:
            try:
                session = UserSession.objects.get(session_key=session_key)
            except UserSession.DoesNotExist:
                pass

        ip = _get_ip(request)

        event = UserEvent.objects.create(
            session=session,
            user=resolved_user,
            event_type=event_type,
            object_type=object_type,
            object_id=str(object_id),
            properties=properties or {},
            ip_address=ip or None,
        )

        # Incrémenter le compteur de la session
        if session:
            from django.db.models import F
            UserSession.objects.filter(pk=session.pk).update(
                events_count=F("events_count") + 1
            )

        # Log brut MongoDB pour historique complet
        _log_to_mongo(resolved_user, event_type, object_type, object_id, properties or {})

        # Incrémenter compteurs Redis temps réel
        _increment_redis_counters(event_type)

        return event

    except Exception as e:
        logger.error(f"track() failed for event '{event_type}': {e}", exc_info=True)
        return None


def track_search(request, query: str, results_count: int = 0, filters: dict = None):
    """Enregistre une recherche utilisateur."""
    try:
        from analytics.models import SearchQuery, UserSession

        resolved_user = request.user if (hasattr(request, "user") and request.user.is_authenticated) else None
        session = None
        session_key = request.COOKIES.get("analytics_session")
        if session_key:
            try:
                session = UserSession.objects.get(session_key=session_key)
            except UserSession.DoesNotExist:
                pass

        SearchQuery.objects.create(
            user=resolved_user,
            session=session,
            query=query[:500],
            query_normalized=query.strip().lower()[:500],
            results_count=results_count,
            filters_applied=filters or {},
            ip_address=_get_ip(request) or None,
        )

        track(request, "search", properties={"query": query, "results_count": results_count})

    except Exception as e:
        logger.error(f"track_search() failed: {e}", exc_info=True)


def track_funnel_step(request, step_name: str, restaurant_id=None, restaurant_name: str = "",
                      order_id=None, order_total=None):
    """
    Avance ou crée un funnel de conversion pour la session courante.
    À appeler à chaque étape clé du parcours d'achat.
    """
    try:
        from analytics.models import ConversionFunnel, UserSession
        from django.utils import timezone

        STEP_MAP = {
            "restaurant_viewed": 1,
            "menu_opened": 2,
            "item_added_to_cart": 3,
            "order_started": 4,
            "payment_initiated": 5,
            "order_confirmed": 6,
        }
        step_num = STEP_MAP.get(step_name, 1)

        resolved_user = request.user if (hasattr(request, "user") and request.user.is_authenticated) else None
        session = None
        session_key = request.COOKIES.get("analytics_session")
        if session_key:
            try:
                session = UserSession.objects.get(session_key=session_key)
            except UserSession.DoesNotExist:
                pass

        # Chercher un funnel ouvert pour ce restaurant/session
        funnel = None
        if session and restaurant_id:
            funnel = ConversionFunnel.objects.filter(
                session=session,
                restaurant_id=restaurant_id,
                converted=False,
            ).first()

        if not funnel:
            funnel = ConversionFunnel.objects.create(
                user=resolved_user,
                session=session,
                restaurant_id=restaurant_id,
                restaurant_name=restaurant_name,
                last_step=step_num,
                last_step_name=step_name,
            )

        # Mettre à jour le funnel
        funnel.last_step = max(funnel.last_step, step_num)
        funnel.last_step_name = step_name
        if funnel.step_timestamps is None:
            funnel.step_timestamps = {}
        funnel.step_timestamps[step_name] = datetime.now(timezone.utc).isoformat()

        if step_name == "order_confirmed" and order_id:
            funnel.converted = True
            funnel.order_id = order_id
            funnel.order_total = order_total
            funnel.completed_at = timezone.now()
            if funnel.started_at:
                funnel.time_to_convert_seconds = int(
                    (funnel.completed_at - funnel.started_at).total_seconds()
                )

        funnel.save()
        return funnel

    except Exception as e:
        logger.error(f"track_funnel_step() failed: {e}", exc_info=True)
        return None


def raise_alert(user, alert_type: str, message: str, severity: str = "warning", details: dict = None):
    """Lève une alerte comportementale sur un utilisateur."""
    try:
        from analytics.models import BehavioralAlert
        # Ne pas créer de doublon si alerte non résolue du même type existe déjà
        existing = BehavioralAlert.objects.filter(
            user=user, alert_type=alert_type, is_resolved=False
        ).first()
        if existing:
            return existing

        return BehavioralAlert.objects.create(
            user=user,
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {},
        )
    except Exception as e:
        logger.error(f"raise_alert() failed: {e}", exc_info=True)
        return None


# Helpers internes

def _get_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _log_to_mongo(user, event_type: str, object_type: str, object_id: str, properties: dict):
    """Log brut dans MongoDB activity_logs."""
    try:
        from core.mongo import get_collection
        col = get_collection("activity_logs")
        col.insert_one({
            "user_id": str(user.id) if user else None,
            "action": event_type,
            "object_type": object_type,
            "object_id": object_id,
            "metadata": properties,
            "timestamp": datetime.now(timezone.utc),
            "source": "analytics_tracker",
        })
    except Exception as e:
        logger.debug(f"MongoDB log failed (non-bloquant): {e}")


def _increment_redis_counters(event_type: str):
    """
    REDIS : performance temps réel — incrémente les compteurs d'événements
    avec TTL 1h pour stats temps réel (événements/min, événements/heure).
    """
    try:
        from core.redis_client import get_redis
        r = get_redis()
        now = datetime.now(timezone.utc)
        # Compteur par heure
        hour_key = f"analytics:events:{event_type}:{now.strftime('%Y%m%d%H')}"
        r.incr(hour_key)
        r.expire(hour_key, 7 * 24 * 3600)  # TTL 7 jours
        # Compteur global
        r.incr(f"analytics:events:total:{event_type}")
    except Exception as e:
        logger.debug(f"Redis counter failed (non-bloquant): {e}")
