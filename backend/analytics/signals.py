"""
Signaux Django - mise à jour automatique des profils analytiques.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from collections import defaultdict
from decimal import Decimal

logger = logging.getLogger("analytics.signals")


@receiver(post_save, sender="orders.Order")
def on_order_saved(sender, instance, created, **kwargs):
    """Après chaque Order, rafraichir le profil analytique du client."""
    try:
        from analytics.services import refresh_user_analytics_profile
        refresh_user_analytics_profile(instance.client)
    except Exception as e:
        logger.error(f"Signal on_order_saved failed: {e}")


@receiver(post_save, sender="analytics.UserEvent")
def on_event_saved(sender, instance, created, **kwargs):
    """Après un événement de paiement échoué, alerte."""
    if not created or not instance.user:
        return
    try:
        if instance.event_type == "payment_failed":
            from analytics.models import UserEvent
            from analytics.tracker import raise_alert
            count = UserEvent.objects.filter(
                user=instance.user, event_type="payment_failed"
            ).count()
            if count >= 3:
                raise_alert(
                    instance.user,
                    "multiple_failed_payments",
                    f"{count} tentatives de paiement échouées",
                    severity="critical",
                    details={"failed_count": count},
                )
    except Exception as e:
        logger.error(f"Signal on_event_saved failed: {e}")


@receiver(post_save, sender="analytics.ItemInteraction")
def on_item_interaction(sender, instance, created, **kwargs):
    """Après chaque ItemInteraction, recalculer le profil de goûts."""
    if not created:
        return
    try:
        _refresh_taste_profile(instance.user)
    except Exception as e:
        logger.error(f"Signal on_item_interaction failed: {e}")


def _refresh_taste_profile(user):
    """Recalcule le UserTasteProfile depuis les ItemInteractions pondérées."""
    from analytics.models import ItemInteraction, UserTasteProfile

    interactions = ItemInteraction.objects.filter(user=user).order_by("-timestamp")[:200]

    tag_scores = defaultdict(int)
    item_scores = defaultdict(int)
    restaurant_scores = defaultdict(int)
    option_freq = defaultdict(int)
    prices = []
    total_score = 0

    for inter in interactions:
        w = inter.weight
        for tag in inter.item_tags:
            tag_scores[tag] += w
        item_scores[inter.item_id] += w
        restaurant_scores[str(inter.restaurant_id)] += w
        for opt in inter.selected_options:
            if opt.get("label"):
                option_freq[opt["label"]] += 1
        if inter.item_price:
            prices.append(float(inter.item_price))
        total_score += w

    favorite_tags = [
        {"tag": t, "score": s}
        for t, s in sorted(tag_scores.items(), key=lambda x: -x[1]) if s > 0
    ][:15]
    top_item_ids = [k for k, v in sorted(item_scores.items(), key=lambda x: -x[1]) if v > 0][:20]
    avoided_item_ids = [k for k, v in item_scores.items() if v < 0][:10]
    frequent_options = [
        {"label": l, "frequency": f}
        for l, f in sorted(option_freq.items(), key=lambda x: -x[1])
    ][:10]

    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    max_price = round(max(prices) * 1.3, 2) if prices else None

    UserTasteProfile.objects.update_or_create(
        user=user,
        defaults={
            "favorite_tags": favorite_tags,
            "top_item_ids": top_item_ids,
            "avoided_item_ids": avoided_item_ids,
            "restaurant_scores": {k: v for k, v in restaurant_scores.items() if v > 0},
            "avg_item_price": Decimal(str(avg_price)) if avg_price else None,
            "max_comfortable_price": Decimal(str(max_price)) if max_price else None,
            "frequent_options": frequent_options,
            "total_interactions": interactions.count(),
            "total_score": total_score,
        },
    )
