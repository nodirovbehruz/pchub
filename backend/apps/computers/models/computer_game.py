from django.db import models
from django.utils.translation import gettext_lazy as _


class ComputerGame(models.Model):
    """
    Many-to-many relationship between computers and games
    Tracks which games are installed on which computers
    """

    # Relationships
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.CASCADE,
        related_name="installed_games",
        help_text=_("Computer"),
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="installations",
        help_text=_("Installed game"),
    )

    # Installation Data
    is_installed = models.BooleanField(
        default=True, help_text=_("Is game currently installed?")
    )
    installed_version = models.CharField(
        max_length=50, blank=True, default="",
        help_text=_("Version currently installed on this PC (for auto-update diff)."),
    )
    install_path = models.CharField(
        max_length=500, blank=True, help_text=_("Game installation path")
    )
    install_size_gb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Installation size in GB"),
    )

    # Timestamps
    installed_at = models.DateTimeField(
        auto_now_add=True, help_text=_("When game was installed")
    )
    last_played = models.DateTimeField(
        null=True, blank=True, help_text=_("Last time game was played")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "computer_games"
        verbose_name = _("Computer Game")
        verbose_name_plural = _("Computer Games")
        unique_together = [["computer", "game"]]
        ordering = ["-last_played", "game__name"]
        indexes = [
            models.Index(fields=["computer", "is_installed"]),
            models.Index(fields=["game"]),
            models.Index(fields=["-last_played"]),
        ]

    def __str__(self):
        return f"{self.game.name} on {self.computer.name}"
