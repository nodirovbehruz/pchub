from django.db import models
from django.utils.translation import gettext_lazy as _


class Tag(models.Model):
    """Tag/Genre model for categorizing games"""

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Tag name (e.g., Action, RPG, Multiplayer)"),
    )
    slug = models.SlugField(
        max_length=100, unique=True, help_text=_("URL-friendly tag name")
    )
    description = models.TextField(blank=True, help_text=_("Tag description"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "game_tags"
        verbose_name = _("Game Tag")
        verbose_name_plural = _("Game Tags")
        ordering = ["name"]

    def __str__(self):
        return self.name
