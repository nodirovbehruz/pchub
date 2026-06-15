from django.db import models
from .game import GamePlatform, Game

class ClubAccount(models.Model):
    platform = models.CharField(
        max_length=20,
        choices=GamePlatform.choices,
        verbose_name="Платформа"
    )
    login = models.CharField(max_length=255, verbose_name="Логин (Email/Username)")
    password = models.CharField(max_length=255, verbose_name="Пароль")
    
    # Is the account active and allowed for player usage?
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    # Is currently attached to a computer playing a game?
    is_in_use = models.BooleanField(default=False, verbose_name="В использовании")
    
    # Relation to games it owns
    games = models.ManyToManyField(
        Game, 
        blank=True, 
        related_name="club_accounts",
        verbose_name="Игры на аккаунте"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Клубный аккаунт"
        verbose_name_plural = "Клубные аккаунты"
        ordering = ["platform", "login"]

    def __str__(self):
        return f"{self.get_platform_display()} - {self.login}"

    @classmethod
    def acquire_for_game(cls, game_id, club=None):
        """Atomically check out ONE free, active account that owns the game.

        Returns the locked ClubAccount or None if none free. Uses a conditional
        UPDATE so two concurrent launches can NEVER grab the same shared account
        (the old plain BooleanField had no guarded checkout → double-assignment →
        platform kick). Always pair with release().
        """
        from django.db import transaction
        with transaction.atomic():
            qs = (cls.objects.select_for_update(skip_locked=True)
                  .filter(is_active=True, is_in_use=False, games__id=game_id))
            if club is not None:
                qs = qs.filter(games__club=club) if hasattr(cls, "club") else qs
            acc = qs.first()
            if acc is None:
                return None
            # Guarded flip — only succeeds if it's still free.
            updated = cls.objects.filter(pk=acc.pk, is_in_use=False).update(is_in_use=True)
            if not updated:
                return None
            acc.is_in_use = True
            return acc

    def release(self):
        """Return the account to the pool (idempotent)."""
        type(self).objects.filter(pk=self.pk).update(is_in_use=False)
        self.is_in_use = False
