"""
Tests : stockage menu MongoDB, invalidation cache Redis, upload images plats.
"""
import io
from unittest.mock import patch, MagicMock, call
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from accounts.models import User
from restaurants.models import Restaurant


# MENU (MongoDB)


class MenuMongoDBTest(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.owner = User.objects.create_user(
            email="owner@test.com", password="pass", role="admin"
        )
        self.restaurant = Restaurant.objects.create(
            name="Chez Mama Africa", owner=self.owner,
            address="Akwa, Douala", is_active=True
        )
        self.client_api.force_authenticate(user=self.owner)

    @patch("restaurants.views.invalidate_menu_cache")
    @patch("restaurants.views.get_collection")
    def test_menu_stored_in_mongodb(self, mock_get_col, mock_invalidate):
        """
        Après PUT /menu/, le menu est mis à jour dans MongoDB et PAS dans PostgreSQL.
        """
        mock_col = MagicMock()
        # find_one retourne None (pas de menu existant)
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        menu_payload = {
            "restaurant_id": str(self.restaurant.id),
            "categories": [
                {
                    "name": "Plats principaux",
                    "items": [
                        {
                            "name": "Poulet DG",
                            "price": 3500,
                            "description": "Poulet sauté avec légumes",
                            "available": True,
                        }
                    ],
                }
            ],
        }

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/"
        response = self.client_api.put(url, menu_payload, format="json")

        self.assertEqual(response.status_code, 200)

        # Vérifie que MongoDB update_one a été appelé (menu stocké dans MongoDB)
        mock_col.update_one.assert_called_once()
        args, kwargs = mock_col.update_one.call_args
        self.assertEqual(args[0]["restaurant_id"], str(self.restaurant.id))
        self.assertTrue(kwargs.get("upsert", False))

        # Vérifie qu'aucun modèle Django PostgreSQL de type "Menu" n'existe
        from django.apps import apps
        menu_models = [m for m in apps.get_models() if "menu" in m.__name__.lower()]
        self.assertEqual(len(menu_models), 0, "Les menus ne doivent PAS être dans PostgreSQL")

    @patch("restaurants.views.get_cached_menu")
    @patch("restaurants.views.invalidate_menu_cache")
    @patch("restaurants.views.get_collection")
    def test_menu_cache_invalidation(self, mock_get_col, mock_invalidate, mock_cached):
        """
        Après PUT /menu/, la clé Redis menu:{id} doit être invalidée.
        """
        mock_col = MagicMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col
        mock_cached.return_value = None

        menu_payload = {
            "restaurant_id": str(self.restaurant.id),
            "categories": [{"name": "Boissons", "items": [{"name": "Jus", "price": 500}]}],
        }

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/"
        response = self.client_api.put(url, menu_payload, format="json")

        self.assertEqual(response.status_code, 200)
        mock_invalidate.assert_called_once_with(str(self.restaurant.id))

    @patch("restaurants.views.get_cached_menu")
    @patch("restaurants.views.get_collection")
    def test_menu_read_from_cache_when_present(self, mock_get_col, mock_cached):
        """
        GET /menu/ : si le cache Redis contient le menu, MongoDB ne doit PAS être appelé.
        """
        cached_menu = {
            "restaurant_id": str(self.restaurant.id),
            "categories": [],
            "_cache": "HIT (Redis)",
        }
        mock_cached.return_value = cached_menu

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["_cache"], "HIT (Redis)")
        # MongoDB ne doit pas être consulté
        mock_get_col.assert_not_called()

    @patch("restaurants.views.get_cached_menu")
    @patch("restaurants.views.set_cached_menu")
    @patch("restaurants.views.get_collection")
    def test_menu_read_from_mongodb_when_cache_miss(self, mock_get_col, mock_set_cache, mock_cached):
        """
        GET /menu/ : si le cache Redis est vide, MongoDB est lu puis le résultat mis en cache.
        """
        mock_cached.return_value = None  # Cache miss
        mock_col = MagicMock()
        mock_col.find_one.return_value = {
            "_id": "some_mongo_id",
            "restaurant_id": str(self.restaurant.id),
            "categories": [],
        }
        mock_get_col.return_value = mock_col

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["_cache"], "MISS (MongoDB)")
        # Redis doit être mis à jour
        mock_set_cache.assert_called_once()

    @patch("restaurants.views.get_cached_menu")
    @patch("restaurants.views.get_collection")
    def test_menu_returns_404_when_not_found(self, mock_get_col, mock_cached):
        """
        GET /menu/ : si le menu n'existe ni en cache ni en MongoDB -> 404.
        """
        mock_cached.return_value = None
        mock_col = MagicMock()
        mock_col.find_one.return_value = None
        mock_get_col.return_value = mock_col

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, 404)

    @patch("restaurants.views.invalidate_menu_cache")
    @patch("restaurants.views.get_collection")
    def test_put_menu_preserves_existing_photos(self, mock_get_col, mock_invalidate):
        """
        PUT /menu/ : les photos existantes des items ne doivent PAS être écrasées
        si le payload ne les inclut pas.
        """
        existing_item_id = "item-abc-123"
        existing_photos = ["http://server/media/menus/resto/item/photo.jpg"]

        mock_col = MagicMock()
        # find_one retourne un menu existant avec des photos
        mock_col.find_one.return_value = {
            "restaurant_id": str(self.restaurant.id),
            "categories": [
                {
                    "name": "Plats",
                    "items": [
                        {
                            "id": existing_item_id,
                            "name": "Poulet DG",
                            "price": 3500,
                            "photos": existing_photos,
                        }
                    ],
                }
            ],
        }
        mock_get_col.return_value = mock_col

        # Le PUT ne fournit PAS de photos pour cet item
        menu_payload = {
            "categories": [
                {
                    "name": "Plats",
                    "items": [
                        {
                            "id": existing_item_id,
                            "name": "Poulet DG mis à jour",
                            "price": 3800,
                            # Pas de "photos" dans le payload
                        }
                    ],
                }
            ],
        }

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/"
        response = self.client_api.put(url, menu_payload, format="json")

        self.assertEqual(response.status_code, 200)

        # Vérifier que update_one a été appelé
        mock_col.update_one.assert_called_once()
        # Récupérer les données passées à $set
        call_args = mock_col.update_one.call_args
        set_data = call_args[0][1]["$set"]

        # Les photos existantes doivent être réinjectées
        items_in_payload = set_data["categories"][0]["items"]
        self.assertEqual(
            items_in_payload[0]["photos"],
            existing_photos,
            "Les photos existantes doivent être préservées lors d'un PUT sans photos"
        )



# IMAGES DES PLATS


class MenuItemImagesTest(TestCase):
    def setUp(self):
        self.client_api = APIClient()
        self.owner = User.objects.create_user(
            email="owner_img@test.com", password="pass", role="admin"
        )
        self.restaurant = Restaurant.objects.create(
            name="Photo Resto", owner=self.owner,
            address="Douala", is_active=True
        )
        self.item_id = "item-photo-001"
        self.client_api.force_authenticate(user=self.owner)

    def _make_image_file(self, name="photo.jpg", content=b"fake_jpeg_content"):
        """Crée un fichier image factice pour les tests."""
        return SimpleUploadedFile(
            name=name,
            content=content,
            content_type="image/jpeg",
        )

    @patch("restaurants.views.upload_item_images")
    def test_upload_images_success(self, mock_upload):
        """
        POST /menu/items/{item_id}/images/ : upload réussi, retourne les URLs.
        """
        expected_photos = [
            f"http://testserver/media/menus/{self.restaurant.id}/{self.item_id}/20240101_abc12345.jpg"
        ]
        mock_upload.return_value = expected_photos

        image_file = self._make_image_file()
        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.post(
            url,
            {"images": image_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["photos"], expected_photos)
        self.assertEqual(data["uploaded_count"], 1)
        self.assertEqual(data["photos_count"], 1)

        # Vérifie que upload_item_images a été appelé avec les bons args
        mock_upload.assert_called_once()
        call_kwargs = mock_upload.call_args
        self.assertEqual(call_kwargs[1]["restaurant_id"], str(self.restaurant.id))
        self.assertEqual(call_kwargs[1]["item_id"], self.item_id)

    @patch("restaurants.views.upload_item_images")
    def test_upload_multiple_images(self, mock_upload):
        """Upload de 3 images en une seule requête."""
        expected_photos = [
            f"http://testserver/media/menus/{self.restaurant.id}/{self.item_id}/img1.jpg",
            f"http://testserver/media/menus/{self.restaurant.id}/{self.item_id}/img2.jpg",
            f"http://testserver/media/menus/{self.restaurant.id}/{self.item_id}/img3.png",
        ]
        mock_upload.return_value = expected_photos

        files = [
            self._make_image_file("img1.jpg"),
            self._make_image_file("img2.jpg"),
            self._make_image_file("img3.png", content_type="image/png") if False
            else self._make_image_file("img3.png"),
        ]

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.post(
            url,
            {"images": files},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["photos_count"], 3)
        self.assertEqual(response.json()["uploaded_count"], 3)

    def test_upload_requires_authentication(self):
        """Upload sans authentification -> 401."""
        anon_client = APIClient()
        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = anon_client.post(url, {"images": self._make_image_file()}, format="multipart")
        self.assertEqual(response.status_code, 401)

    def test_upload_requires_ownership(self):
        """Un utilisateur non propriétaire ne peut pas uploader."""
        other_user = User.objects.create_user(
            email="other@test.com", password="pass", role="client"
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = other_client.post(
            url,
            {"images": self._make_image_file()},
            format="multipart",
        )
        self.assertEqual(response.status_code, 403)

    def test_upload_no_file_returns_400(self):
        """POST sans fichier -> 400."""
        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.post(url, {}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("images", response.json()["error"].lower())

    @patch("restaurants.views.upload_item_images")
    def test_upload_limit_exceeded_returns_400(self, mock_upload):
        """Tentative d'upload au-delà de la limite -> 400."""
        mock_upload.side_effect = ValueError(
            "Limite atteinte : ce plat a déjà 5 images (max 5)."
        )

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.post(
            url,
            {"images": self._make_image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Limite", response.json()["error"])

    @patch("restaurants.views.get_item_images")
    def test_get_item_images(self, mock_get_images):
        """GET /images/ : retourne la liste des photos et les métadonnées."""
        mock_get_images.return_value = {
            "item_id": self.item_id,
            "item_name": "Poulet DG",
            "photos": ["http://server/media/menus/r/i/photo.jpg"],
            "photos_count": 1,
            "slots_remaining": 4,
            "max_images": 5,
        }

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["photos_count"], 1)
        self.assertEqual(data["slots_remaining"], 4)
        self.assertEqual(data["max_images"], 5)

    @patch("restaurants.views.delete_item_image")
    def test_delete_image_success(self, mock_delete):
        """DELETE /images/ : supprime une image et retourne la liste restante."""
        image_url = f"http://testserver/media/menus/{self.restaurant.id}/{self.item_id}/photo.jpg"
        mock_delete.return_value = []  # Plus d'images restantes

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.delete(
            url,
            {"image_url": image_url},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["photos_count"], 0)
        mock_delete.assert_called_once_with(
            str(self.restaurant.id), self.item_id, image_url
        )

    @patch("restaurants.views.delete_item_image")
    def test_delete_image_not_found_returns_400(self, mock_delete):
        """DELETE avec une URL inconnue -> 400."""
        mock_delete.side_effect = ValueError("Image 'http://other.com/img.jpg' introuvable.")

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.delete(
            url,
            {"image_url": "http://other.com/img.jpg"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_delete_image_missing_param_returns_400(self):
        """DELETE sans image_url -> 400."""
        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/"
        response = self.client_api.delete(url, {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("image_url", response.json()["error"])

    @patch("restaurants.views.reorder_item_images")
    def test_reorder_images_success(self, mock_reorder):
        """PATCH /images/reorder/ : réordonner les images."""
        new_order = [
            f"http://testserver/media/menus/{self.restaurant.id}/{self.item_id}/b.jpg",
            f"http://testserver/media/menus/{self.restaurant.id}/{self.item_id}/a.jpg",
        ]
        mock_reorder.return_value = new_order

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/reorder/"
        response = self.client_api.patch(
            url,
            {"photos": new_order},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["photos"], new_order)
        mock_reorder.assert_called_once_with(str(self.restaurant.id), self.item_id, new_order)

    @patch("restaurants.views.reorder_item_images")
    def test_reorder_invalid_urls_returns_400(self, mock_reorder):
        """PATCH /images/reorder/ avec des URLs inconnues -> 400."""
        mock_reorder.side_effect = ValueError("URLs incorrectes.")

        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/reorder/"
        response = self.client_api.patch(
            url,
            {"photos": ["http://fake.com/img.jpg"]},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_reorder_missing_payload_returns_400(self):
        """PATCH /images/reorder/ sans payload -> 400."""
        url = f"/api/v1/restaurants/{self.restaurant.id}/menu/items/{self.item_id}/images/reorder/"
        response = self.client_api.patch(url, {}, format="json")
        self.assertEqual(response.status_code, 400)



# SERVICE IMAGE (tests unitaires)

class ImageServiceTest(TestCase):
    """Tests unitaires du service image_service.py (sans I/O disque réel)."""

    def setUp(self):
        self.restaurant_id = "550e8400-e29b-41d4-a716-446655440000"
        self.item_id = "item-unit-test-001"

        # Menu MongoDB simulé
        self.mock_menu = {
            "restaurant_id": self.restaurant_id,
            "categories": [
                {
                    "name": "Plats",
                    "items": [
                        {
                            "id": self.item_id,
                            "name": "Poulet DG",
                            "price": 3500,
                            "photos": ["http://server/media/menus/r/i/existing.jpg"],
                        }
                    ],
                }
            ],
        }

    @patch("restaurants.image_service.get_collection")
    def test_get_item_images_returns_correct_structure(self, mock_get_col):
        """get_item_images retourne la structure attendue."""
        from restaurants.image_service import get_item_images

        mock_col = MagicMock()
        mock_col.find_one.return_value = self.mock_menu
        mock_get_col.return_value = mock_col

        result = get_item_images(self.restaurant_id, self.item_id)

        self.assertEqual(result["item_id"], self.item_id)
        self.assertEqual(result["item_name"], "Poulet DG")
        self.assertEqual(result["photos_count"], 1)
        self.assertEqual(result["slots_remaining"], 4)  # 5 - 1

    @patch("restaurants.image_service.get_collection")
    def test_get_item_images_raises_on_unknown_item(self, mock_get_col):
        """get_item_images lève ValueError si l'item n'existe pas."""
        from restaurants.image_service import get_item_images

        mock_col = MagicMock()
        mock_col.find_one.return_value = self.mock_menu
        mock_get_col.return_value = mock_col

        with self.assertRaises(ValueError) as ctx:
            get_item_images(self.restaurant_id, "item-inexistant")

        self.assertIn("introuvable", str(ctx.exception))

    @patch("restaurants.image_service.get_collection")
    def test_get_item_images_raises_on_missing_menu(self, mock_get_col):
        """get_item_images lève ValueError si le menu n'existe pas."""
        from restaurants.image_service import get_item_images

        mock_col = MagicMock()
        mock_col.find_one.return_value = None  # Pas de menu
        mock_get_col.return_value = mock_col

        with self.assertRaises(ValueError) as ctx:
            get_item_images(self.restaurant_id, self.item_id)

        self.assertIn("menu", str(ctx.exception).lower())

    @patch("restaurants.image_service.invalidate_menu_cache")
    @patch("restaurants.image_service.get_collection")
    def test_delete_removes_url_from_mongodb(self, mock_get_col, mock_invalidate):
        """delete_item_image appelle $pull sur MongoDB et invalide le cache Redis."""
        from restaurants.image_service import delete_item_image

        mock_col = MagicMock()
        mock_col.find_one.return_value = self.mock_menu
        mock_get_col.return_value = mock_col

        url_to_delete = "http://server/media/menus/r/i/existing.jpg"

        with patch("restaurants.image_service.os.remove"):
            with patch("restaurants.image_service.Path") as mock_path:
                mock_path.return_value.__truediv__.return_value.exists.return_value = False
                remaining = delete_item_image(self.restaurant_id, self.item_id, url_to_delete)

        # MongoDB $pull doit être appelé
        mock_col.update_one.assert_called_once()
        update_call = mock_col.update_one.call_args[0][1]
        self.assertIn("$pull", update_call)

        # Cache Redis doit être invalidé
        mock_invalidate.assert_called_once_with(self.restaurant_id)

        # La photo doit être retirée de la liste
        self.assertEqual(remaining, [])

    @patch("restaurants.image_service.get_collection")
    def test_delete_raises_on_unknown_url(self, mock_get_col):
        """delete_item_image lève ValueError si l'URL n'existe pas dans MongoDB."""
        from restaurants.image_service import delete_item_image

        mock_col = MagicMock()
        mock_col.find_one.return_value = self.mock_menu
        mock_get_col.return_value = mock_col

        with self.assertRaises(ValueError) as ctx:
            delete_item_image(self.restaurant_id, self.item_id, "http://fake.com/nonexistent.jpg")

        self.assertIn("introuvable", str(ctx.exception))

    @patch("restaurants.image_service.invalidate_menu_cache")
    @patch("restaurants.image_service.get_collection")
    def test_reorder_replaces_photos_array(self, mock_get_col, mock_invalidate):
        """reorder_item_images remplace le tableau photos dans MongoDB."""
        from restaurants.image_service import reorder_item_images

        existing_url = "http://server/media/menus/r/i/existing.jpg"
        mock_menu_two_photos = {
            "restaurant_id": self.restaurant_id,
            "categories": [{
                "name": "Plats",
                "items": [{
                    "id": self.item_id,
                    "name": "Poulet DG",
                    "price": 3500,
                    "photos": [existing_url, "http://server/media/menus/r/i/second.jpg"],
                }]
            }]
        }

        mock_col = MagicMock()
        mock_col.find_one.return_value = mock_menu_two_photos
        mock_get_col.return_value = mock_col

        new_order = [
            "http://server/media/menus/r/i/second.jpg",
            existing_url,
        ]
        result = reorder_item_images(self.restaurant_id, self.item_id, new_order)

        self.assertEqual(result, new_order)
        mock_col.update_one.assert_called_once()
        mock_invalidate.assert_called_once_with(self.restaurant_id)

    @patch("restaurants.image_service.get_collection")
    def test_reorder_raises_on_wrong_urls(self, mock_get_col):
        """reorder_item_images lève ValueError si les URLs soumises ne correspondent pas."""
        from restaurants.image_service import reorder_item_images

        mock_col = MagicMock()
        mock_col.find_one.return_value = self.mock_menu
        mock_get_col.return_value = mock_col

        with self.assertRaises(ValueError) as ctx:
            reorder_item_images(self.restaurant_id, self.item_id, [
                "http://server/media/menus/r/i/existing.jpg",
                "http://FAKE.com/extra_url.jpg",  # URL inconnue
            ])

        self.assertIn("incorrecte", str(ctx.exception))
