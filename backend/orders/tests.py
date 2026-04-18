"""
Test : rollback de transaction si solde insuffisant.
POSTGRES : ACID requis - ni Order ni WalletTransaction ne doivent être créés.
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User, Wallet
from restaurants.models import Restaurant
from orders.models import Order, WalletTransaction
import uuid


MOCK_MENU = {
    "restaurant_id": None,  # sera défini dans setUp
    "categories": [
        {
            "name": "Plats",
            "items": [
                {
                    "id": "item-001",
                    "name": "Poulet DG",
                    "price": 3500,
                    "description": "Délicieux",
                    "available": True,
                }
            ],
        }
    ],
}


class OrderTransactionTest(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.user = User.objects.create_user(
            email="client@test.com", password="pass123", role="client"
        )
        # Solde insuffisant : 1000 XAF alors que l'item coûte 3500 XAF
        Wallet.objects.filter(user=self.user).update(balance=1000)

        self.owner = User.objects.create_user(email="owner@test.com", password="pass", role="admin")
        self.restaurant = Restaurant.objects.create(
            name="Chez Mama", owner=self.owner, address="Douala", is_active=True
        )
        MOCK_MENU["restaurant_id"] = str(self.restaurant.id)
        self.client_api.force_authenticate(user=self.user)

    @patch("orders.services.set_order_status")
    @patch("orders.services.log_activity")
    @patch("orders.services.get_collection")
    def test_order_transaction_rollback(self, mock_get_col, mock_log, mock_redis):
        """
        Si le solde est insuffisant, AUCUNE Order ni WalletTransaction ne doit être
        créée dans PostgreSQL - le ROLLBACK annule tout.
        """
        mock_col = MagicMock()
        mock_col.find_one.return_value = MOCK_MENU.copy()
        mock_get_col.return_value = mock_col

        orders_before = Order.objects.count()
        transactions_before = WalletTransaction.objects.count()
        wallet_balance_before = Wallet.objects.get(user=self.user).balance

        payload = {
            "restaurant_id": str(self.restaurant.id),
            "items": [{"item_id": "item-001", "quantity": 1}],
        }

        response = self.client_api.post("/api/v1/orders/", payload, format="json")

        # La requête doit échouer avec INSUFFICIENT_FUNDS
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INSUFFICIENT_FUNDS")

        # Vérification ROLLBACK PostgreSQL - aucune Order créée
        self.assertEqual(Order.objects.count(), orders_before,
                         "ROLLBACK échoué : une Order a été créée malgré le solde insuffisant")

        # Vérification ROLLBACK PostgreSQL - aucune WalletTransaction créée
        self.assertEqual(WalletTransaction.objects.count(), transactions_before,
                         "ROLLBACK échoué : une WalletTransaction a été créée")

        # Vérification ROLLBACK PostgreSQL - le solde n'a pas changé
        wallet_balance_after = Wallet.objects.get(user=self.user).balance
        self.assertEqual(wallet_balance_before, wallet_balance_after,
                         "ROLLBACK échoué : le solde a été modifié")

        # Redis NE doit PAS avoir été appelé (la transaction a échoué avant)
        mock_redis.assert_not_called()

    @patch("orders.services.set_order_status")
    @patch("orders.services.log_activity")
    @patch("orders.services.get_collection")
    def test_order_success_with_sufficient_funds(self, mock_get_col, mock_log, mock_redis):
        """
        Avec un solde suffisant, l'Order et la WalletTransaction sont bien créées.
        """
        # Recharger le wallet avec suffisamment
        Wallet.objects.filter(user=self.user).update(balance=50000)

        mock_col = MagicMock()
        mock_col.find_one.return_value = MOCK_MENU.copy()
        mock_get_col.return_value = mock_col

        payload = {
            "restaurant_id": str(self.restaurant.id),
            "items": [{"item_id": "item-001", "quantity": 2}],
        }

        response = self.client_api.post("/api/v1/orders/", payload, format="json")

        self.assertEqual(response.status_code, 201)

        # Vérifier que l'Order a été créée en PostgreSQL
        self.assertEqual(Order.objects.count(), 1)

        # Vérifier que la WalletTransaction a été créée
        self.assertEqual(WalletTransaction.objects.count(), 1)
        tx = WalletTransaction.objects.first()
        self.assertEqual(tx.type, "debit")
        self.assertEqual(tx.amount, 7000)  # 3500 * 2

        # Vérifier le solde déduit
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, 43000)  # 50000 - 7000

        # Redis doit avoir été notifié
        mock_redis.assert_called_once()
