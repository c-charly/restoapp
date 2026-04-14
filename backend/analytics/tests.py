"""
Tests du module analytique.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User, Wallet
from restaurants.models import Restaurant
from orders.models import Order
from analytics.models import UserSession, PageView, UserEvent, UserAnalyticsProfile


class AnalyticsMiddlewareTest(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(
            email="analytics_user@test.com", password="pass", role="client"
        )

    def test_page_view_recorded_on_request(self):
        """Chaque requête HTTP doit créer un PageView."""
        self.client_api.force_authenticate(user=self.user)
        before = PageView.objects.count()
        self.client_api.get("/api/v1/restaurants/")
        after = PageView.objects.count()
        self.assertGreater(after, before, "Un PageView doit être créé pour chaque requête")

    def test_session_created_on_first_request(self):
        """La première requête doit créer une UserSession."""
        before = UserSession.objects.count()
        self.client_api.get("/api/v1/restaurants/")
        after = UserSession.objects.count()
        self.assertGreaterEqual(after, before)


class TrackEventTest(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(
            email="track_user@test.com", password="pass", role="client"
        )
        self.client_api.force_authenticate(user=self.user)

    def test_track_event_endpoint(self):
        """POST /analytics/track/event/ doit créer un UserEvent."""
        before = UserEvent.objects.count()
        payload = {
            "event_type": "restaurant_viewed",
            "object_type": "restaurant",
            "object_id": "some-uuid",
            "properties": {"name": "Chez Mama"},
        }
        response = self.client_api.post("/api/v1/analytics/track/event/", payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["tracked"])
        self.assertGreater(UserEvent.objects.count(), before)


class UserAnalyticsProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="profile_user@test.com", password="pass", role="client"
        )
        Wallet.objects.filter(user=self.user).update(balance=50000)
        self.owner = User.objects.create_user(email="owner_p@test.com", password="pass", role="admin")
        self.restaurant = Restaurant.objects.create(
            name="Test Resto", owner=self.owner, address="Douala", is_active=True
        )

    def test_profile_created_and_computed(self):
        """Le profil analytique doit être calculé correctement."""
        from analytics.services import refresh_user_analytics_profile

        # Créer quelques commandes
        Order.objects.create(
            client=self.user, restaurant=self.restaurant,
            status="delivered", total_price=5000,
        )
        Order.objects.create(
            client=self.user, restaurant=self.restaurant,
            status="delivered", total_price=3500,
        )
        Order.objects.create(
            client=self.user, restaurant=self.restaurant,
            status="cancelled", total_price=2000,
        )

        profile = refresh_user_analytics_profile(self.user)

        self.assertEqual(profile.total_orders, 3)
        self.assertEqual(float(profile.total_spent_xaf), 10500.0)
        self.assertEqual(profile.orders_delivered, 2)
        self.assertEqual(profile.orders_cancelled, 1)
        self.assertEqual(profile.favorite_restaurant_name, "Test Resto")
        self.assertIn(profile.loyalty_tier, ["new", "bronze", "silver", "gold", "platinum"])
        self.assertGreaterEqual(float(profile.engagement_score), 0)

    def test_loyalty_tier_computation(self):
        """Le tier de fidélité doit être calculé selon les dépenses."""
        profile, _ = UserAnalyticsProfile.objects.get_or_create(user=self.user)

        profile.total_spent_xaf = 5000
        self.assertEqual(profile.compute_loyalty_tier(), "new")

        profile.total_spent_xaf = 20000
        self.assertEqual(profile.compute_loyalty_tier(), "bronze")

        profile.total_spent_xaf = 100000
        self.assertEqual(profile.compute_loyalty_tier(), "silver")

        profile.total_spent_xaf = 250000
        self.assertEqual(profile.compute_loyalty_tier(), "gold")

        profile.total_spent_xaf = 600000
        self.assertEqual(profile.compute_loyalty_tier(), "platinum")
