from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ClientSessionStatus(models.TextChoices):
    PLANNED = "planned", _("Planned")     # запланирована (через бронь)
    ACTIVE = "active", _("Active")        # клиент за ПК, играет
    FINISHED = "finished", _("Finished")  # сессия завершилась штатно
    CANCELLED = "cancelled", _("Cancelled")  # отменена досрочно


class ClientSession(models.Model):
    """Operator-facing session of a client on one or more PCs.

    Mirrors SmartShell `ClientSession`. Distinct from `GameSession` (which tracks
    hours per specific game). One session may include multiple PCs (`SessionHost`).
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="client_sessions",
    )

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="client_sessions",
        help_text=_("Null = guest session"),
    )
    guest_session = models.ForeignKey(
        "computers.GuestSession",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="club_session_refs",
        help_text=_("Legacy guest session reference (transitional)"),
    )

    tariff = models.ForeignKey(
        "billing.TariffPlan",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="client_sessions",
    )

    payment = models.ForeignKey(
        "billing.Payment",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="client_sessions",
    )
    shift = models.ForeignKey(
        "billing.Shift",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="client_sessions",
    )

    duration_minutes = models.PositiveIntegerField(default=0)
    elapsed_minutes = models.PositiveIntegerField(default=0)
    total_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
    )
    postpaid = models.BooleanField(
        default=False,
        help_text=_("True for postpay sessions — pay after play"),
    )

    status = models.CharField(
        max_length=12,
        choices=ClientSessionStatus.choices,
        default=ClientSessionStatus.PLANNED,
    )

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "client_sessions"
        verbose_name = _("Client Session")
        verbose_name_plural = _("Client Sessions")
        ordering = ["-started_at", "-created_at"]
        indexes = [
            models.Index(fields=["club", "status"]),
            models.Index(fields=["client"]),
            models.Index(fields=["-started_at"]),
        ]

    def __str__(self):
        who = self.client or "guest"
        return f"Session #{self.id} — {who} [{self.status}]"

    @property
    def time_left_minutes(self):
        return max(0, self.duration_minutes - self.elapsed_minutes)


class SessionHost(models.Model):
    """One PC participating in a ClientSession (M2M with timestamps)."""

    session = models.ForeignKey(
        ClientSession,
        on_delete=models.CASCADE,
        related_name="hosts",
    )
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.CASCADE,
        related_name="session_hosts",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "session_hosts"
        verbose_name = _("Session Host")
        verbose_name_plural = _("Session Hosts")
        unique_together = [("session", "computer")]
        ordering = ["session_id", "started_at"]

    def __str__(self):
        return f"{self.session} on {self.computer}"
