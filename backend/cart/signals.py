"""
Mise à jour automatique de la note du restaurant après chaque notation de plat.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count

logger = logging.getLogger(__name__)


@receiver(post_save, sender="cart.ItemRating")
@receiver(post_delete, sender="cart.ItemRating")
def update_restaurant_rating(sender, instance, **kwargs):
    """
    Recalcule et persiste la note agrégée du restaurant après chaque ItemRating.
    """
    try:
        from cart.models import ItemRating, RestaurantRating

        restaurant = instance.restaurant
        agg = ItemRating.objects.filter(restaurant=restaurant).aggregate(
            avg=Avg("rating"),
            total=Count("id"),
        )

        # Distribution par note (1 à 5)
        distribution = {}
        for star in range(1, 6):
            distribution[str(star)] = ItemRating.objects.filter(
                restaurant=restaurant, rating=star
            ).count()

        RestaurantRating.objects.update_or_create(
            restaurant=restaurant,
            defaults={
                "avg_rating": round(agg["avg"] or 0, 2),
                "total_ratings": agg["total"] or 0,
                "ratings_distribution": distribution,
            },
        )
        logger.info(f"Restaurant {restaurant.name} rating updated -> {agg['avg']}/5")

    except Exception as e:
        logger.error(f"update_restaurant_rating signal failed: {e}")
