from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.games.models import Game
from apps.computers.models import Computer, ComputerGame

@receiver(post_save, sender=Game)
def auto_assign_game_to_computers(sender, instance, created, **kwargs):
    """
    Automatically assign a newly created or activated game to all active computers.
    """
    if instance.is_active:
        # Get all active computers
        active_computers = Computer.objects.filter(is_active=True)
        
        # Create ComputerGame entry for each computer if it doesn't exist
        for computer in active_computers:
            ComputerGame.objects.get_or_create(
                computer=computer,
                game=instance,
                defaults={
                    'is_installed': True,
                    'install_path': instance.executable_path or ''
                }
            )
