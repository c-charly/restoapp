"""
À la création d'un User - créer automatiquement un Wallet associé
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, Wallet


@receiver(post_save, sender=User)
def create_wallet_for_new_user(sender, instance, created, **kwargs):
    """Crée automatiquement un Wallet lors de la création d'un User."""
    if created:
        Wallet.objects.get_or_create(user=instance)
