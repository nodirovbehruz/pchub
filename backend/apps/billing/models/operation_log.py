from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LogAction(models.TextChoices):
    # Sessions
    SESSION_START = "session.start", _("Session started")
    SESSION_END = "session.end", _("Session ended")
    SESSION_TRANSFER = "session.transfer", _("Session transferred")
    SESSION_PENALIZE = "session.penalize", _("Session penalized")
    SESSION_EXTEND = "session.extend", _("Session extended")
    # Payments
    PAYMENT_CREATE = "payment.create", _("Payment created")
    PAYMENT_REFUND = "payment.refund", _("Payment refunded")
    DEPOSIT_TOPUP = "deposit.topup", _("Deposit topped up")
    DEPOSIT_TRANSFER = "deposit.transfer", _("Deposit transferred between clubs")
    # Cash
    CASH_PKO = "cash.pko", _("Cash income (ПКО)")
    CASH_RKO = "cash.rko", _("Cash outcome (РКО)")
    # Shift
    SHIFT_OPEN = "shift.open", _("Shift opened")
    SHIFT_CLOSE = "shift.close", _("Shift closed")
    # Power
    PC_POWER_ON = "pc.power_on", _("PC powered on")
    PC_POWER_OFF = "pc.power_off", _("PC powered off")
    PC_REBOOT = "pc.reboot", _("PC rebooted")
    PC_HIGH_ACCESS = "pc.high_access", _("PC high-access toggled")
    # CRUD
    DB_CREATE = "db.create", _("Record created")
    DB_UPDATE = "db.update", _("Record updated")
    DB_DELETE = "db.delete", _("Record deleted")
    # Auth
    AUTH_LOGIN = "auth.login", _("Employee logged in")
    AUTH_LOGOUT = "auth.logout", _("Employee logged out")


class OperationLog(models.Model):
    """Unified audit log of all operator and system events.

    Used by SmartShell-style Logs page. Search bar matches phone/product/PC name.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="operation_logs",
    )
    shift = models.ForeignKey(
        "billing.Shift",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="operation_logs",
    )

    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="actions_performed",
        help_text=_("Who performed the action (operator/system)"),
    )
    object_type = models.CharField(
        max_length=50, blank=True, default="",
        help_text=_("Model name or 'system'"),
    )
    object_id = models.CharField(max_length=64, blank=True, default="")
    object_repr = models.CharField(
        max_length=200, blank=True, default="",
        help_text=_("Human-readable label of the object"),
    )

    action = models.CharField(max_length=40, choices=LogAction.choices)
    payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "operation_logs"
        verbose_name = _("Operation Log")
        verbose_name_plural = _("Operation Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "-created_at"]),
            models.Index(fields=["shift", "-created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.subject} {self.action} {self.object_repr}"
