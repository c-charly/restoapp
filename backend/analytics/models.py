"""
toutes les données analytiques structurées nécessitent
des FK vers User, des agrégats SQL et des jointures complexes.

Ce module capture TOUT ce qui se passe sur la plateforme :
- Sessions utilisateurs (connexions, durée, device, IP)
- Pages / endpoints visités (avec temps de réponse, user-agent, géoloc IP)
- Événements comportementaux (clics, recherches, paniers abandonnés, etc.)
- Profil d'habitudes consolidé par utilisateur
- Funnel de conversion (visite - commande - review)
- Alertes et anomalies comportementales
"""
import uuid
from django.db import models
from django.utils import timezone
from accounts.models import User


# SESSION UTILISATEUR

class UserSession(models.Model):
    """
    une session est le conteneur de toutes les actions d'une visite.
    Chaque connexion crée une session. Chaque action y est rattachée par FK.
    """
    DEVICE_CHOICES = [
        ("mobile", "Mobile"),
        ("tablet", "Tablette"),
        ("desktop", "Desktop"),
        ("unknown", "Inconnu"),
    ]
    OS_CHOICES = [
        ("android", "Android"),
        ("ios", "iOS"),
        ("windows", "Windows"),
        ("macos", "macOS"),
        ("linux", "Linux"),
        ("unknown", "Inconnu"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sessions", help_text="Null si session anonyme"
    )
    session_key = models.CharField(max_length=64, unique=True, db_index=True)

    # Timing
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_activity_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Réseau
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Appareil
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, default="unknown")
    os = models.CharField(max_length=20, choices=OS_CHOICES, default="unknown")
    os_version = models.CharField(max_length=30, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    browser_version = models.CharField(max_length=30, blank=True)
    user_agent = models.TextField(blank=True)
    screen_resolution = models.CharField(max_length=20, blank=True)
    app_version = models.CharField(max_length=20, blank=True)

    # Provenance
    referrer = models.URLField(blank=True, max_length=500)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)

    # Métriques
    page_views_count = models.PositiveIntegerField(default=0)
    events_count = models.PositiveIntegerField(default=0)
    orders_count = models.PositiveIntegerField(default=0)
    is_bounce = models.BooleanField(default=True)  # True si 1 seule page visitée

    class Meta:
        db_table = "analytics_sessions"
        indexes = [
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["ip_address"]),
            models.Index(fields=["device_type"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        uid = self.user.email if self.user else "anonyme"
        return f"Session {uid} — {self.started_at:%Y-%m-%d %H:%M}"

    def close(self):
        """Ferme la session et calcule la durée."""
        self.ended_at = timezone.now()
        self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())
        self.save(update_fields=["ended_at", "duration_seconds"])


# PAGE / ENDPOINT VISITÉ

class PageView(models.Model):
    """
    chaque requête HTTP tracée avec sa session, son user,
    son temps de réponse. Permet l'analyse des pages les plus consultées,
    des performances et des parcours utilisateur.
    """
    METHOD_CHOICES = [
        ("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"),
        ("PATCH", "PATCH"), ("DELETE", "DELETE"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        UserSession, on_delete=models.CASCADE, related_name="page_views", null=True, blank=True
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="page_views"
    )

    # Requête
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default="GET")
    path = models.CharField(max_length=500, db_index=True)
    query_string = models.TextField(blank=True)
    full_url = models.TextField(blank=True)
    http_status = models.PositiveSmallIntegerField(db_index=True)
    response_time_ms = models.PositiveIntegerField(help_text="Temps de réponse en millisecondes")

    # Contexte
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referer = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    # Données extra
    view_name = models.CharField(max_length=200, blank=True, help_text="Nom Django de la vue")
    extra_data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "analytics_pageviews"
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["path", "timestamp"]),
            models.Index(fields=["http_status"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.method} {self.path} [{self.http_status}] — {self.response_time_ms}ms"


# ÉVÉNEMENTS COMPORTEMENTAUX

class UserEvent(models.Model):
    """
    événements métier précis qui racontent le comportement
    de l'utilisateur : ce qu'il cherche, ce qu'il abandonne, ce qu'il commande.
    """
    EVENT_TYPES = [
        # Navigation
        ("page_view", "Vue de page"),
        ("search", "Recherche"),
        ("filter_applied", "Filtre appliqué"),
        # Restaurant
        ("restaurant_viewed", "Restaurant consulté"),
        ("menu_opened", "Menu ouvert"),
        ("item_viewed", "Item consulté"),
        ("item_added_to_cart", "Item ajouté au panier"),
        ("item_removed_from_cart", "Item retiré du panier"),
        ("cart_abandoned", "Panier abandonné"),
        # Commande
        ("order_started", "Commande démarrée"),
        ("order_confirmed", "Commande confirmée"),
        ("order_cancelled", "Commande annulée"),
        ("order_tracking_opened", "Tracking ouvert"),
        # Paiement
        ("payment_initiated", "Paiement initié"),
        ("payment_success", "Paiement réussi"),
        ("payment_failed", "Paiement échoué"),
        ("wallet_topped_up", "Wallet rechargé"),
        # Review
        ("review_started", "Review démarrée"),
        ("review_submitted", "Review soumise"),
        # Profil
        ("login", "Connexion"),
        ("logout", "Déconnexion"),
        ("register", "Inscription"),
        ("profile_updated", "Profil mis à jour"),
        ("address_added", "Adresse ajoutée"),
        # Livreur
        # ("driver_online", "Livreur connecté"),
        # ("driver_offline", "Livreur déconnecté"),
        # ("delivery_started", "Livraison démarrée"),
        # ("delivery_completed", "Livraison complétée"),
        # Erreurs
        ("error_404", "Page introuvable"),
        ("error_500", "Erreur serveur"),
        ("error_auth", "Erreur d'authentification"),
        ("error_payment", "Erreur paiement"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        UserSession, on_delete=models.CASCADE, related_name="events", null=True, blank=True
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True)

    # Objet concerné
    object_type = models.CharField(
        max_length=50, blank=True,
        help_text="Ex: 'order', 'restaurant', 'menu_item'"
    )
    object_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Données enrichies (libres)
    properties = models.JSONField(
        default=dict, blank=True,
        help_text="Données contextuelles libres : prix, nom plat, restaurant_id, query, etc."
    )

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "analytics_events"
        indexes = [
            models.Index(fields=["user", "event_type", "timestamp"]),
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        uid = self.user.email if self.user else "anonyme"
        return f"{self.event_type} — {uid} — {self.timestamp:%Y-%m-%d %H:%M}"


# PROFIL D'HABITUDES CONSOLIDÉ PAR UTILISATEUR

class UserAnalyticsProfile(models.Model):
    """
    vue consolidée et agrégée des habitudes d'un utilisateur.
    Mis à jour périodiquement (signal ou tâche cron).
    Permet des requêtes rapides sans recalcul à chaque fois.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="analytics_profile"
    )

    # Activité générale
    total_sessions = models.PositiveIntegerField(default=0)
    total_page_views = models.PositiveIntegerField(default=0)
    total_events = models.PositiveIntegerField(default=0)
    avg_session_duration_seconds = models.PositiveIntegerField(default=0)
    avg_pages_per_session = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    first_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_active_ip = models.GenericIPAddressField(null=True, blank=True)
    last_device = models.CharField(max_length=20, blank=True)

    # Commandes
    total_orders = models.PositiveIntegerField(default=0)
    total_spent_xaf = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    avg_order_value_xaf = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    orders_cancelled = models.PositiveIntegerField(default=0)
    orders_delivered = models.PositiveIntegerField(default=0)
    cart_abandonments = models.PositiveIntegerField(default=0)

    # Restaurants favoris
    favorite_restaurant_id = models.UUIDField(null=True, blank=True)
    favorite_restaurant_name = models.CharField(max_length=200, blank=True)
    favorite_restaurant_orders = models.PositiveIntegerField(default=0)

    # Habitudes temporelles
    most_active_hour = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Heure 0-23 où l'utilisateur est le plus actif"
    )
    most_active_day = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Jour 0=Lundi … 6=Dimanche"
    )
    orders_by_hour = models.JSONField(
        default=dict, help_text="{'0': 0, '12': 3, '19': 5, ...}"
    )
    orders_by_day = models.JSONField(
        default=dict, help_text="{'0': 2, '5': 8, ...}"
    )

    # Device & Localisation
    preferred_device = models.CharField(max_length=20, blank=True)
    preferred_os = models.CharField(max_length=20, blank=True)
    primary_city = models.CharField(max_length=100, blank=True)
    primary_country = models.CharField(max_length=100, blank=True)
    known_ips = models.JSONField(default=list, help_text="Liste des IP connues")

    # Recherches & Navigation
    top_search_queries = models.JSONField(
        default=list, help_text="[{'query': 'ndolé', 'count': 12}, ...]"
    )
    top_visited_paths = models.JSONField(
        default=list, help_text="[{'path': '/api/v1/restaurants/', 'count': 45}, ...]"
    )

    # Scoring comportemental
    engagement_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Score 0-100 basé sur fréquence, dépenses et fidélité"
    )
    churn_risk_score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Score 0-100 : probabilité d'abandon (basé sur inactivité)"
    )
    loyalty_tier = models.CharField(
        max_length=20, default="new",
        choices=[
            ("new", "Nouveau"),
            ("bronze", "Bronze"),
            ("silver", "Argent"),
            ("gold", "Or"),
            ("platinum", "Platine"),
        ],
        help_text="Calculé selon total_spent_xaf et total_orders"
    )

    # Reviews
    total_reviews = models.PositiveIntegerField(default=0)
    avg_rating_given = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_user_profiles"

    def __str__(self):
        return f"AnalyticsProfile — {self.user.email} [{self.loyalty_tier}]"

    def compute_loyalty_tier(self):
        """Calcule le tier de fidélité selon les dépenses totales."""
        spent = float(self.total_spent_xaf)
        if spent >= 500_000:
            return "platinum"
        elif spent >= 200_000:
            return "gold"
        elif spent >= 75_000:
            return "silver"
        elif spent >= 15_000:
            return "bronze"
        return "new"

    def compute_engagement_score(self):
        """
        Score d'engagement 0-100 basé sur :
        - Fréquence de connexion (30%)
        - Nombre de commandes (30%)
        - Dépenses totales (20%)
        - Fidélité restaurant (10%)
        - Reviews (10%)
        """
        score = 0.0
        # Fréquence sessions (max 50 sessions = 30 pts)
        score += min(self.total_sessions / 50, 1.0) * 30
        # Commandes (max 20 commandes = 30 pts)
        score += min(self.total_orders / 20, 1.0) * 30
        # Dépenses (max 200 000 XAF = 20 pts)
        score += min(float(self.total_spent_xaf) / 200_000, 1.0) * 20
        # Restaurant favori (max 10 commandes = 10 pts)
        score += min(self.favorite_restaurant_orders / 10, 1.0) * 10
        # Reviews (max 5 reviews = 10 pts)
        score += min(self.total_reviews / 5, 1.0) * 10
        return round(score, 2)


# FUNNEL DE CONVERSION

class ConversionFunnel(models.Model):
    """
    suit le parcours de chaque tentative de commande,
    de la vue restaurant jusqu'au paiement final.
    Permet de détecter exactement où les utilisateurs abandonnent.
    """
    STEP_CHOICES = [
        (1, "restaurant_viewed"),
        (2, "menu_opened"),
        (3, "item_added_to_cart"),
        (4, "order_started"),
        (5, "payment_initiated"),
        (6, "order_confirmed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="funnels"
    )
    session = models.ForeignKey(
        UserSession, on_delete=models.CASCADE, related_name="funnels", null=True, blank=True
    )

    restaurant_id = models.UUIDField(null=True, blank=True)
    restaurant_name = models.CharField(max_length=200, blank=True)

    # Étape atteinte
    last_step = models.PositiveSmallIntegerField(choices=STEP_CHOICES, default=1)
    last_step_name = models.CharField(max_length=50, blank=True)
    converted = models.BooleanField(default=False, db_index=True)
    order_id = models.UUIDField(null=True, blank=True)
    order_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Timings de chaque étape (timestamp ISO)
    step_timestamps = models.JSONField(
        default=dict,
        help_text="{'restaurant_viewed': '...', 'menu_opened': '...', ...}"
    )
    time_to_convert_seconds = models.PositiveIntegerField(null=True, blank=True)

    # Abandon
    abandoned_at_step = models.PositiveSmallIntegerField(null=True, blank=True)
    abandon_reason = models.CharField(max_length=200, blank=True)

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "analytics_funnels"
        indexes = [
            models.Index(fields=["user", "started_at"]),
            models.Index(fields=["converted"]),
            models.Index(fields=["restaurant_id"]),
        ]

    def __str__(self):
        status = "Converti" if self.converted else f"Abandonné étape {self.abandoned_at_step}"
        return f"Funnel {self.user} — {status}"


# RECHERCHES

class SearchQuery(models.Model):
    """
    chaque recherche tracée pour comprendre
    ce que les utilisateurs veulent trouver sur la plateforme.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="searches"
    )
    session = models.ForeignKey(
        UserSession, on_delete=models.CASCADE, null=True, blank=True, related_name="searches"
    )

    query = models.CharField(max_length=500, db_index=True)
    query_normalized = models.CharField(max_length=500, db_index=True, help_text="Minuscules, trimé")
    results_count = models.PositiveIntegerField(default=0)
    clicked_result_id = models.CharField(max_length=100, blank=True)
    clicked_result_type = models.CharField(max_length=50, blank=True)
    filters_applied = models.JSONField(default=dict)

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "analytics_searches"
        indexes = [
            models.Index(fields=["query_normalized"]),
            models.Index(fields=["user", "timestamp"]),
        ]

    def __str__(self):
        return f'Recherche "{self.query}" — {self.results_count} résultats'


# ALERTES COMPORTEMENTALES

class BehavioralAlert(models.Model):
    """
    alertes automatiques levées quand un pattern
    anormal est détecté : trop de tentatives échouées, comportement suspect, etc.
    """
    ALERT_TYPES = [
        ("multiple_failed_payments", "Plusieurs paiements échoués"),
        ("unusual_location", "Connexion depuis emplacement inhabituel"),
        ("high_cart_abandonment", "Taux d'abandon panier élevé"),
        ("inactive_user", "Utilisateur inactif 30+ jours"),
        ("high_cancellation_rate", "Taux d'annulation élevé"),
        ("suspicious_activity", "Activité suspecte (trop de requêtes)"),
        ("multiple_accounts_same_ip", "Plusieurs comptes depuis même IP"),
        ("churn_risk", "Risque de départ détecté"),
    ]
    SEVERITY_CHOICES = [
        ("info", "Information"),
        ("warning", "Avertissement"),
        ("critical", "Critique"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="behavioral_alerts"
    )
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES, db_index=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default="info")
    message = models.TextField()
    details = models.JSONField(default=dict)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "analytics_alerts"
        indexes = [
            models.Index(fields=["user", "alert_type"]),
            models.Index(fields=["is_resolved", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.alert_type} — {self.user.email}"


# INTERACTIONS AVEC LES PLATS (pour recommandation)

class ItemInteraction(models.Model):
    """
    trace toutes les interactions d'un utilisateur
    avec les plats du menu. Alimente directement le moteur de recommandation.

    Types d'interaction capturés :
      viewed        - plat vu dans le feed ou le menu
      detail_opened - fiche détail ouverte
      added_to_cart - ajouté au panier
      removed_from_cart - retiré du panier
      ordered       - plat commandé et payé
      rated_positive - noté 4-5 étoiles
      rated_negative - noté 1-2 étoiles
      shared        - partagé (réseau social)
    """
    INTERACTION_TYPES = [
        ("viewed", "Vu"),
        ("detail_opened", "Détail ouvert"),
        ("added_to_cart", "Ajouté au panier"),
        ("removed_from_cart", "Retiré du panier"),
        ("ordered", "Commandé"),
        ("rated_positive", "Note positive (4-5)"),
        ("rated_negative", "Note négative (1-2)"),
        ("shared", "Partagé"),
    ]

    # Poids de chaque interaction pour le scoring de recommandation
    INTERACTION_WEIGHTS = {
        "viewed": 1,
        "detail_opened": 2,
        "added_to_cart": 5,
        "removed_from_cart": -2,
        "ordered": 10,
        "rated_positive": 8,
        "rated_negative": -5,
        "shared": 6,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="item_interactions"
    )
    item_id = models.CharField(max_length=100, db_index=True, help_text="ID MongoDB de l'item")
    item_name = models.CharField(max_length=200)
    restaurant_id = models.UUIDField(db_index=True)
    interaction_type = models.CharField(max_length=30, choices=INTERACTION_TYPES, db_index=True)

    # Tags de l'item au moment de l'interaction (pour profil de goûts)
    item_tags = models.JSONField(default=list)
    item_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Options choisies si ajout au panier / commande
    selected_options = models.JSONField(default=list)

    # Score de pertinence pour la recommandation
    weight = models.SmallIntegerField(default=1, help_text="Poids de l'interaction")

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "analytics_item_interactions"
        indexes = [
            models.Index(fields=["user", "item_id"]),
            models.Index(fields=["user", "interaction_type", "timestamp"]),
            models.Index(fields=["item_id", "interaction_type"]),
            models.Index(fields=["restaurant_id", "interaction_type"]),
        ]

    def save(self, *args, **kwargs):
        self.weight = self.INTERACTION_WEIGHTS.get(self.interaction_type, 1)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} → {self.interaction_type} → {self.item_name}"


class UserTasteProfile(models.Model):
    """
    profil de goûts consolidé par utilisateur.
    Mis à jour automatiquement par signal après chaque ItemInteraction.
    Utilisé par le moteur de recommandation pour personnaliser le feed.
    """
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="taste_profile"
    )

    # Tags préférés (triés par score décroissant)
    # Structure : [{"tag": "populaire", "score": 42}, {"tag": "grillé", "score": 18}, ...]
    favorite_tags = models.JSONField(default=list)

    # Items préférés (score élevé)
    top_item_ids = models.JSONField(default=list, help_text="IDs MongoDB des items préférés")

    # Items à éviter (score négatif)
    avoided_item_ids = models.JSONField(default=list)

    # Restaurants par score d'affinité
    restaurant_scores = models.JSONField(
        default=dict,
        help_text="{'restaurant_uuid': 42, ...}"
    )

    # Tranche de prix préférée
    avg_item_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_comfortable_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Habitudes d'options (quelles options sont souvent choisies)
    frequent_options = models.JSONField(
        default=list,
        help_text="[{'label': 'Extra sauce', 'frequency': 12}, ...]"
    )

    # Totaux
    total_interactions = models.PositiveIntegerField(default=0)
    total_score = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "analytics_taste_profiles"

    def __str__(self):
        return f"TasteProfile — {self.user.email} ({self.total_interactions} interactions)"
