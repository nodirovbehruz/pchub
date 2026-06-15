from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CommandType(models.TextChoices):
    INSTALL = "install", _("Install")
    REINSTALL = "reinstall", _("Reinstall")
    UNINSTALL = "uninstall", _("Uninstall")
    UPDATE = "update", _("Update")
    UPDATE_APP = "update_app", _("Update Application")
    UNLOCK = "unlock", _("Unlock (Open Access)")
    LOCK = "lock", _("Lock (Close Access)")
    REBOOT = "reboot", _("Reboot")
    SHUTDOWN = "shutdown", _("Shutdown")
    WOL = "wol", _("Wake on LAN")
    LOGIN = "login", _("Login User")
    TRANSFER = "transfer", _("Transfer Session")
    HIGH_ACCESS = "high_access", _("Grant High Access")
    HIGH_ACCESS_OFF = "high_access_off", _("Revoke High Access")
    KILL_GAMES = "kill_games", _("Kill Game Processes")





class CommandStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    IN_PROGRESS = "in_progress", _("In Progress")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")


class ComputerCommand(models.Model):
    """
    Command queue for remote software management on gaming PCs.
    Admin creates commands; the PC client polls and executes them.
    """

    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.CASCADE,
        related_name="commands",
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commands",
    )
    command_type = models.CharField(max_length=20, choices=CommandType.choices)
    status = models.CharField(
        max_length=20,
        choices=CommandStatus.choices,
        default=CommandStatus.PENDING,
    )
    # Flexible payload: installer_url, install_args, uninstall_path, etc.
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_commands",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "computer_commands"
        verbose_name = _("Computer Command")
        verbose_name_plural = _("Computer Commands")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["computer", "status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        game_name = self.game.name if self.game else "unknown"
        return (
            f"{self.command_type} {game_name} on {self.computer.name} [{self.status}]"
        )
