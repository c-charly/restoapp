"""
Service de gestion des images des plats du menu.

Architecture :
  - Les fichiers image sont sauvegardés sur disque : /media/menus/{restaurant_id}/{item_id}/
  - Leurs URLs publiques (/media/...) sont stockées dans le document MongoDB de l'item
  - MongoDB reste la source de vérité pour les métadonnées du plat (photos = liste d'URLs)
  - Redis cache est invalidé à chaque modification

Règles :
  - Max 5 images par plat (configurable via settings.MENU_ITEM_MAX_IMAGES_PER_ITEM)
  - Extensions acceptées : .jpg .jpeg .png .webp (settings.MENU_ITEM_ALLOWED_IMAGE_EXTENSIONS)
  - Taille max : 5 Mo par image (settings.FILE_UPLOAD_MAX_MEMORY_SIZE)
  - Nommage fichier : {timestamp}_{uuid4_short}.{ext}  (évite les collisions)
  - Un item peut appartenir à n'importe quelle catégorie du menu, la recherche
    parcourt toutes les catégories du document MongoDB du restaurant

"""
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

from core.mongo import get_collection
from core.redis_client import invalidate_menu_cache

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────────────

def _item_upload_dir(restaurant_id: str, item_id: str) -> Path:
    """Retourne le chemin absolu du dossier d'images d'un item."""
    return Path(settings.MEDIA_ROOT) / "menus" / restaurant_id / item_id


def _item_url_prefix(restaurant_id: str, item_id: str) -> str:
    """Retourne le préfixe d'URL public pour les images d'un item."""
    return f"{settings.MEDIA_URL}menus/{restaurant_id}/{item_id}/"


def _validate_image_file(image_file) -> str:
    """
    Valide l'extension et la taille d'un fichier image.
    Retourne l'extension normalisée (.jpg, .png…) ou lève ValueError.
    """
    allowed = getattr(settings, "MENU_ITEM_ALLOWED_IMAGE_EXTENSIONS", [".jpg", ".jpeg", ".png", ".webp"])
    max_size = getattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE", 5 * 1024 * 1024)

    name = image_file.name or ""
    ext = os.path.splitext(name)[1].lower()
    if ext not in allowed:
        raise ValueError(
            f"Extension '{ext}' non autorisée. Acceptées : {', '.join(allowed)}"
        )

    # Vérification taille (InMemoryUploadedFile expose .size)
    if hasattr(image_file, "size") and image_file.size > max_size:
        raise ValueError(
            f"Image trop lourde : {image_file.size // 1024} Ko. Max : {max_size // 1024} Ko."
        )

    return ext


def _find_item_in_menu(menu_doc: dict, item_id: str):
    """
    Parcourt toutes les catégories du menu MongoDB et retourne
    (category_index, item_index, item_dict) ou (None, None, None).
    """
    for cat_idx, category in enumerate(menu_doc.get("categories", [])):
        for item_idx, item in enumerate(category.get("items", [])):
            if str(item.get("id", "")) == item_id:
                return cat_idx, item_idx, item
    return None, None, None


def _build_item_array_filter_path(cat_idx: int, item_idx: int) -> str:
    """
    Construit le chemin MongoDB pour cibler un item précis dans
    le tableau imbriqué categories[cat_idx].items[item_idx].
    On utilise le filtre positionnel avec arrayFilters pour une mise à jour chirurgicale.
    """
    return f"categories.{cat_idx}.items.{item_idx}.photos"


# ─────────────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────────────

def upload_item_images(
    restaurant_id: str,
    item_id: str,
    image_files: list,
    request=None,
) -> list:
    """
    Uploade une ou plusieurs images pour un plat et met à jour MongoDB.

    Étapes :
    1. Vérifie que le menu et l'item existent dans MongoDB
    2. Valide chaque fichier (extension, taille)
    3. Vérifie la limite max d'images par item
    4. Sauvegarde les fichiers sur disque : /media/menus/{restaurant_id}/{item_id}/
    5. Construit les URLs publiques
    6. Met à jour MongoDB : ajoute les nouvelles URLs au tableau `photos` de l'item
    7. Invalide le cache Redis du menu

    Retourne la liste complète des photos (anciennes + nouvelles).
    """
    max_images = getattr(settings, "MENU_ITEM_MAX_IMAGES_PER_ITEM", 5)

    # 1. Lire le menu depuis MongoDB 
    col = get_collection("menus")
    menu_doc = col.find_one({"restaurant_id": restaurant_id})
    if not menu_doc:
        raise ValueError(f"Aucun menu trouvé pour le restaurant {restaurant_id}.")

    cat_idx, item_idx, item_doc = _find_item_in_menu(menu_doc, item_id)
    if item_doc is None:
        raise ValueError(f"Plat '{item_id}' introuvable dans le menu.")

    existing_photos = list(item_doc.get("photos", []))

    # 2. Vérifier la limite 
    slots_remaining = max_images - len(existing_photos)
    if slots_remaining <= 0:
        raise ValueError(
            f"Limite atteinte : ce plat a déjà {len(existing_photos)} images "
            f"(max {max_images}). Supprimez-en avant d'en ajouter."
        )
    if len(image_files) > slots_remaining:
        raise ValueError(
            f"Trop d'images : vous essayez d'uploader {len(image_files)} images "
            f"mais il ne reste que {slots_remaining} slot(s) disponible(s)."
        )

    # 3. Valider les fichiers 
    validated = []
    for img in image_files:
        ext = _validate_image_file(img)
        validated.append((img, ext))

    # 4. Créer le dossier de stockage
    upload_dir = _item_upload_dir(restaurant_id, item_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 5. Sauvegarder les fichiers et construire les URLs 
    new_urls = []
    saved_paths = []  # Pour rollback en cas d'erreur MongoDB

    try:
        for img, ext in validated:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            short_uuid = uuid.uuid4().hex[:8]
            filename = f"{timestamp}_{short_uuid}{ext}"
            file_path = upload_dir / filename

            with open(file_path, "wb") as f:
                for chunk in img.chunks():
                    f.write(chunk)

            saved_paths.append(file_path)

            # Construire l'URL publique absolue si request disponible, sinon relative
            relative_url = f"{settings.MEDIA_URL}menus/{restaurant_id}/{item_id}/{filename}"
            if request is not None:
                absolute_url = request.build_absolute_uri(relative_url)
                new_urls.append(absolute_url)
            else:
                new_urls.append(relative_url)

        # 6. Mettre à jour MongoDB
        # MONGODB : on fait un $push pour ajouter les URLs
        # sans écraser les photos existantes
        photos_field = _build_item_array_filter_path(cat_idx, item_idx)

        col.update_one(
            {"restaurant_id": restaurant_id},
            {
                "$push": {
                    photos_field: {"$each": new_urls}
                },
                "$set": {
                    "updated_at": datetime.now(timezone.utc)
                },
            },
        )

    except Exception as e:
        # Rollback : supprimer les fichiers déjà écrits
        for path in saved_paths:
            try:
                os.remove(path)
            except OSError:
                pass
        raise RuntimeError(f"Erreur lors de l'upload : {e}")

    # 7. Invalider le cache Redis 
    # REDIS : le cache doit refléter les nouvelles images
    invalidate_menu_cache(restaurant_id)

    # Retourner la liste complète (anciennes + nouvelles)
    return existing_photos + new_urls


def delete_item_image(restaurant_id: str, item_id: str, image_url: str) -> list:
    """
    Supprime une image spécifique d'un plat.

    Étapes :
    1. Vérifie que l'image appartient bien à cet item dans MongoDB
    2. Supprime le fichier sur disque
    3. Retire l'URL du tableau `photos` dans MongoDB
    4. Invalide le cache Redis

    Retourne la liste restante des photos après suppression.

    MONGODB : $pull retire l'URL du tableau sans migration.
    """
    # 1. Lire le menu 
    col = get_collection("menus")
    menu_doc = col.find_one({"restaurant_id": restaurant_id})
    if not menu_doc:
        raise ValueError(f"Aucun menu trouvé pour le restaurant {restaurant_id}.")

    cat_idx, item_idx, item_doc = _find_item_in_menu(menu_doc, item_id)
    if item_doc is None:
        raise ValueError(f"Plat '{item_id}' introuvable dans le menu.")

    current_photos = list(item_doc.get("photos", []))

    # Normaliser l'URL pour comparaison (chemin relatif ou absolu)
    def _normalize(url: str) -> str:
        """Extrait le chemin relatif depuis une URL absolue ou relative."""
        media_url = settings.MEDIA_URL
        # Trouver la partie /media/... dans l'URL
        idx = url.find(media_url)
        return url[idx:] if idx != -1 else url

    normalized_target = _normalize(image_url)
    matched_url = None
    for photo in current_photos:
        if _normalize(photo) == normalized_target:
            matched_url = photo
            break

    if matched_url is None:
        raise ValueError(f"Image '{image_url}' introuvable dans les photos de ce plat.")

    # 2. Supprimer le fichier physique
    # Extraire le chemin relatif depuis /media/
    relative_path = _normalize(matched_url).lstrip("/")  # media/menus/.../fichier.jpg
    # Retirer le préfixe "media/"
    media_relative = relative_path[len(settings.MEDIA_URL.strip("/")):]  # menus/.../fichier.jpg
    file_path = Path(settings.MEDIA_ROOT) / media_relative.lstrip("/")

    if file_path.exists():
        try:
            os.remove(file_path)
            logger.info(f"Image supprimée du disque : {file_path}")
        except OSError as e:
            logger.warning(f"Impossible de supprimer le fichier {file_path} : {e}")
    else:
        logger.warning(f"Fichier introuvable sur disque (URL fantôme) : {file_path}")

    # 3. Mettre à jour MongoDB
    # MONGODB : $pull retire la valeur exacte du tableau
    photos_field = _build_item_array_filter_path(cat_idx, item_idx)

    col.update_one(
        {"restaurant_id": restaurant_id},
        {
            "$pull": {photos_field: matched_url},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )

    # 4. Invalider le cache Redis
    invalidate_menu_cache(restaurant_id)

    # Retourner la liste restante
    remaining = [p for p in current_photos if p != matched_url]
    return remaining


def reorder_item_images(restaurant_id: str, item_id: str, ordered_urls: list) -> list:
    """
    Réordonne les images d'un plat.

    `ordered_urls` doit contenir exactement les mêmes URLs que celles déjà
    stockées, dans le nouvel ordre souhaité.

    MONGODB : on remplace simplement le tableau `photos`
    par la version réordonnée. Pas de migration Django requise.
    """
    col = get_collection("menus")
    menu_doc = col.find_one({"restaurant_id": restaurant_id})
    if not menu_doc:
        raise ValueError(f"Aucun menu trouvé pour le restaurant {restaurant_id}.")

    cat_idx, item_idx, item_doc = _find_item_in_menu(menu_doc, item_id)
    if item_doc is None:
        raise ValueError(f"Plat '{item_id}' introuvable dans le menu.")

    current_photos = set(item_doc.get("photos", []))
    submitted = set(ordered_urls)

    # Vérifier que les URLs soumises correspondent exactement aux existantes
    if current_photos != submitted:
        extra = submitted - current_photos
        missing = current_photos - submitted
        msg_parts = []
        if extra:
            msg_parts.append(f"URLs inconnues : {list(extra)[:3]}")
        if missing:
            msg_parts.append(f"URLs manquantes : {list(missing)[:3]}")
        raise ValueError(f"Liste d'URLs incorrecte. {'; '.join(msg_parts)}")

    # Mettre à jour MongoDB avec le nouvel ordre
    photos_field = _build_item_array_filter_path(cat_idx, item_idx)
    col.update_one(
        {"restaurant_id": restaurant_id},
        {
            "$set": {
                photos_field: ordered_urls,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    # Invalider le cache Redis
    invalidate_menu_cache(restaurant_id)

    return ordered_urls


def get_item_images(restaurant_id: str, item_id: str) -> dict:
    """
    Retourne les métadonnées images d'un plat depuis MongoDB.

    Retourne :
    {
        "item_id": "...",
        "item_name": "Poulet DG",
        "photos": ["url1", "url2", ...],
        "photos_count": 2,
        "slots_remaining": 3,
        "max_images": 5,
    }
    """
    max_images = getattr(settings, "MENU_ITEM_MAX_IMAGES_PER_ITEM", 5)

    col = get_collection("menus")
    menu_doc = col.find_one({"restaurant_id": restaurant_id})
    if not menu_doc:
        raise ValueError(f"Aucun menu trouvé pour le restaurant {restaurant_id}.")

    _, _, item_doc = _find_item_in_menu(menu_doc, item_id)
    if item_doc is None:
        raise ValueError(f"Plat '{item_id}' introuvable dans le menu.")

    photos = list(item_doc.get("photos", []))
    return {
        "item_id": item_id,
        "item_name": item_doc.get("name", ""),
        "photos": photos,
        "photos_count": len(photos),
        "slots_remaining": max(0, max_images - len(photos)),
        "max_images": max_images,
    }
