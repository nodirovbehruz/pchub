from django.db import models
from django.utils.translation import gettext_lazy as _


class SplashType(models.TextChoices):
    SOFT = "soft", _("Soft")
    SNOWFLAKE = "snowflake", _("SnowFlake")
    SMARTLOCK_TV = "smartlock_tv", _("SmartLock TV")


class ShellTheme(models.Model):
    """Per-club appearance settings of the client Shell.

    SmartShell «Кастомизация»: colors, logo, club poster, splash screens.
    """

    club = models.OneToOneField(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="shell_theme",
    )

    logo = models.ImageField(upload_to="shell/logo/", blank=True, null=True)
    poster = models.ImageField(upload_to="shell/poster/", blank=True, null=True)

    primary_color = models.CharField(max_length=20, default="#6366f1")
    accent_color = models.CharField(max_length=20, default="#a855f7")
    secondary_color = models.CharField(max_length=20, default="#ec4899")

    splash_type = models.CharField(
        max_length=20, choices=SplashType.choices, default=SplashType.SOFT,
    )
    splash_enabled = models.BooleanField(default=True)
    splash_delay_seconds = models.PositiveIntegerField(default=60)

    background_image = models.ImageField(upload_to="shell/bg/", blank=True, null=True)
    tint_effect = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shell_themes"
        verbose_name = _("Shell Theme")
        verbose_name_plural = _("Shell Themes")

    def __str__(self):
        return f"Theme of {self.club}"
