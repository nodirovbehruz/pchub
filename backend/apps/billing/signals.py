from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserBalance

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_balance(sender, instance, created, **kwargs):
    """Automatically create a UserBalance record for every new user."""
    if created:
        UserBalance.objects.get_or_create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_balance(sender, instance, **kwargs):
    """Ensure the balance record is saved if the user is updated."""
    if hasattr(instance, 'balance'):
        instance.balance.save()
