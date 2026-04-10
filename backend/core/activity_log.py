"""
MONGODB : es métadonnées de log varient selon l'action, pas de schéma fixe.
"""
import logging
from datetime import datetime, timezone
from .mongo import get_collection

logger = logging.getLogger(__name__)


def log_activity(user_id: str, action: str, metadata: dict = None):
    """
    Insère un log dans MongoDB collection `activity_logs`.
    """
    try:
        col = get_collection("activity_logs")
        col.insert_one({
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {},
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as e:
        logger.warning(f"MongoDB log_activity failed: {e}")
