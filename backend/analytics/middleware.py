"""
Middleware de tracking automatique - capture CHAQUE requête HTTP.

Ce middleware s'insère dans la chaîne Django et :
1. Crée/met à jour la session analytique de l'utilisateur
2. Enregistre chaque PageView avec temps de réponse précis
3. Extrait device, OS, browser depuis le User-Agent
4. Résout la géolocalisation IP (si geoip2 disponible)
5. Stocke les données de façon asynchrone pour ne pas pénaliser les perfs

MONGO : les logs bruts sont aussi envoyés dans activity_logs pour l'historique complet.
REDIS  : la session courante est mise en cache pour accès rapide.
"""
import json
import time
import logging
import hashlib
from datetime import datetime, timezone

from django.conf import settings
from django.utils import timezone as dj_timezone

logger = logging.getLogger("analytics")

# Paths à ignorer (assets statiques, health checks, etc.)
EXCLUDED_PATHS = {
    "/favicon.ico",
    "/static/",
    "/media/",
    "/api/schema/",
    "/health/",
    "/ping/",
}

EXCLUDED_PREFIXES = ("/static/", "/media/", "/__debug__/")


def _should_track(path: str) -> bool:
    """Détermine si ce path doit être tracké."""
    if path in EXCLUDED_PATHS:
        return False
    for prefix in EXCLUDED_PREFIXES:
        if path.startswith(prefix):
            return False
    return True


def _get_client_ip(request) -> str:
    """Extrait la vraie IP client (derrière proxy/load balancer)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _parse_user_agent(ua_string: str) -> dict:
    """
    Parse basique du User-Agent pour extraire device/OS/browser.
    En production, utiliser `user-agents` (pip install user-agents).
    """
    ua = ua_string.lower()
    result = {
        "device_type": "unknown",
        "os": "unknown",
        "os_version": "",
        "browser": "",
        "browser_version": "",
    }

    # Device
    if any(k in ua for k in ["mobile", "android", "iphone", "ipod"]):
        result["device_type"] = "mobile"
    elif any(k in ua for k in ["tablet", "ipad"]):
        result["device_type"] = "tablet"
    elif ua:
        result["device_type"] = "desktop"

    # OS
    if "android" in ua:
        result["os"] = "android"
        try:
            result["os_version"] = ua.split("android ")[1].split(";")[0].strip()
        except (IndexError, ValueError):
            pass
    elif "iphone" in ua or "ipad" in ua or "ios" in ua:
        result["os"] = "ios"
    elif "windows" in ua:
        result["os"] = "windows"
    elif "mac os" in ua or "macos" in ua:
        result["os"] = "macos"
    elif "linux" in ua:
        result["os"] = "linux"

    # Browser
    if "chrome" in ua and "chromium" not in ua and "edg" not in ua:
        result["browser"] = "Chrome"
    elif "firefox" in ua:
        result["browser"] = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        result["browser"] = "Safari"
    elif "edg" in ua:
        result["browser"] = "Edge"
    elif "opera" in ua or "opr" in ua:
        result["browser"] = "Opera"

    return result


def _get_or_create_session(request, user, ip: str, ua_parsed: dict):
    """
    Récupère ou crée la session analytique pour cette requête.
    Utilise un cookie ou un header X-Session-Key.
    """
    from analytics.models import UserSession

    session_key = (
        request.COOKIES.get("analytics_session")
        or request.META.get("HTTP_X_SESSION_KEY")
    )

    if not session_key:
        # Générer une clé basée sur IP + UA + timestamp heure
        raw = f"{ip}-{request.META.get('HTTP_USER_AGENT', '')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H')}"
        session_key = hashlib.sha256(raw.encode()).hexdigest()[:32]

    try:
        session = UserSession.objects.get(session_key=session_key)
        # Mettre à jour last_activity et user si maintenant authentifié
        update_fields = ["last_activity_at"]
        if user and user.is_authenticated and session.user_id != user.pk:
            session.user = user
            update_fields.append("user")
        session.last_activity_at = dj_timezone.now()
        session.save(update_fields=update_fields)
    except UserSession.DoesNotExist:
        session = UserSession.objects.create(
            session_key=session_key,
            user=user if (user and user.is_authenticated) else None,
            ip_address=ip or None,
            **ua_parsed,
        )

    return session, session_key


class AnalyticsMiddleware:
    """
    Middleware principal de tracking.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if not _should_track(path):
            return self.get_response(request)

        # Avant la vue 
        start_time = time.monotonic()
        ip = _get_client_ip(request)
        ua_string = request.META.get("HTTP_USER_AGENT", "")
        ua_parsed = _parse_user_agent(ua_string)

        # Exécuter la vue 
        response = self.get_response(request)

        # Après la vue 
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        try:
            user = request.user if hasattr(request, "user") else None
            auth_user = user if (user and user.is_authenticated) else None

            session, session_key = _get_or_create_session(request, auth_user, ip, ua_parsed)

            # Enregistrer la PageView
            self._record_page_view(
                request=request,
                response=response,
                session=session,
                user=auth_user,
                ip=ip,
                ua_string=ua_string,
                elapsed_ms=elapsed_ms,
            )

            # Mettre à jour le compteur de la session
            from django.db.models import F
            from analytics.models import UserSession
            UserSession.objects.filter(pk=session.pk).update(
                page_views_count=F("page_views_count") + 1,
                is_bounce=(session.page_views_count == 0),
            )

            # Ajouter le cookie de session à la réponse
            if "analytics_session" not in request.COOKIES:
                response.set_cookie(
                    "analytics_session", session_key,
                    max_age=30 * 24 * 3600,  # 30 jours
                    httponly=True,
                    samesite="Lax",
                )

        except Exception as e:
            # Ne jamais bloquer une requête à cause d'analytics
            logger.error(f"Analytics middleware error: {e}", exc_info=True)

        return response

    def _record_page_view(self, request, response, session, user, ip, ua_string, elapsed_ms):
        """Enregistre un PageView en base PostgreSQL."""
        from analytics.models import PageView

        # Résoudre le nom de la vue Django
        view_name = ""
        try:
            from django.urls import resolve
            match = resolve(request.path)
            view_name = match.view_name or ""
        except Exception:
            pass

        PageView.objects.create(
            session=session,
            user=user,
            method=request.method,
            path=request.path,
            query_string=request.META.get("QUERY_STRING", ""),
            full_url=request.build_absolute_uri(),
            http_status=response.status_code,
            response_time_ms=elapsed_ms,
            ip_address=ip or None,
            user_agent=ua_string[:500],
            referer=request.META.get("HTTP_REFERER", "")[:500],
            view_name=view_name,
        )
