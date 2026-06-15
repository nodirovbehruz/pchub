from django.db import models
from django.utils.translation import gettext_lazy as _


class ClubSettings(models.Model):
    """Operational settings for a club, stored as a flexible JSON blob."""

    club = models.OneToOneField(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="settings",
        verbose_name=_("Club"),
    )
    data = models.JSONField(
        _("Settings data"),
        default=dict,
        blank=True,
        help_text=_("All operational settings as a JSON object"),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Club Settings")
        verbose_name_plural = _("Club Settings")

    def __str__(self):
        return f"Settings for {self.club}"

    @classmethod
    def get_value(cls, club_id, key, default=None):
        """Read a single operational setting for a club (None-safe). Central accessor
        so backend logic can enforce the toggles configured in the admin panel."""
        if not club_id:
            return default
        try:
            obj = cls.objects.filter(club_id=club_id).only("data").first()
            if not obj or not isinstance(obj.data, dict):
                return default
            val = obj.data.get(key, default)
            return default if val is None else val
        except Exception:
            return default

    @classmethod
    def get_bool(cls, club_id, key, default=False):
        return bool(cls.get_value(club_id, key, default))

    @classmethod
    def get_int(cls, club_id, key, default=0):
        try:
            return int(cls.get_value(club_id, key, default) or 0)
        except (TypeError, ValueError):
            return default
