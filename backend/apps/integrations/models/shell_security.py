from django.db import models
from django.utils.translation import gettext_lazy as _


class ShellSecurity(models.Model):
    """Per-club shell security settings.

    SmartShell «Безопасность»: high-access password, hidden drives,
    external storage ban, Chrome download ban.
    """

    club = models.OneToOneField(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="shell_security",
    )

    high_access_password = models.CharField(
        max_length=128, default="pasw0rd",
        help_text=_("Password to enter Ctrl+Alt+P high-access mode. Change from default!"),
    )

    tightvnc_enabled = models.BooleanField(default=False)

    hidden_drives = models.JSONField(
        default=list, blank=True,
        help_text=_("List of drive letters hidden in Shell, e.g. ['C', 'D']"),
    )

    block_external_storage = models.BooleanField(default=False)
    block_chrome_downloads = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shell_security"
        verbose_name = _("Shell Security")
        verbose_name_plural = _("Shell Security")

    def __str__(self):
        return f"Security of {self.club}"


class BlockedApp(models.Model):
    """A window/app pattern that Shell will block from running."""

    security = models.ForeignKey(
        ShellSecurity, on_delete=models.CASCADE,
        related_name="blocked_apps",
    )
    name_mask = models.CharField(
        max_length=200, blank=True, default="",
        help_text=_("Window title mask, supports wildcard '*' (e.g. *SmartShell*)"),
    )
    window_class = models.CharField(
        max_length=120, blank=True, default="",
        help_text=_("Window class (e.g. CabinetWClass, ConsoleWindowClass)"),
    )
    note = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "shell_blocked_apps"
        verbose_name = _("Blocked App")
        verbose_name_plural = _("Blocked Apps")

    def __str__(self):
        return self.name_mask or self.window_class or f"BlockedApp #{self.id}"
