from django.db import models
from django.utils.translation import gettext_lazy as _


class IntegrationType(models.TextChoices):
    TELEGRAM = "telegram", _("Telegram")
    CLOUDPAYMENTS = "cloudpayments", _("CloudPayments")
    SBP = "sbp", _("СБП (Russia)")
    KASPI_QR = "kaspi_qr", _("Kaspi QR (Kazakhstan)")
    KASPI_ONLINE = "kaspi_online", _("Kaspi Online")
    STRIPE = "stripe", _("Stripe")
    KKM = "kkm", _("Cash register (Kkm-Server)")
    SMARTGAMER = "smartgamer", _("SmartGamer mobile")
    SMARTKIOSK = "smartkiosk", _("SmartKiosk")
    HARDWARE_CONTROLLER = "hardware_controller", _("Hardware controller")


class Integration(models.Model):
    """External integration configuration per club.

    SmartShell «Интеграции» — Telegram notifications, CloudPayments, СБП,
    Kaspi QR/online, Stripe, Kkm-Server, etc.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="integrations",
    )
    type = models.CharField(max_length=30, choices=IntegrationType.choices)

    is_active = models.BooleanField(default=False)
    config = models.JSONField(
        default=dict, blank=True,
        help_text=_("Type-specific configuration (api keys, secrets, options)"),
    )
    notify_event_types = models.JSONField(
        default=list, blank=True,
        help_text=_("Which event types to send (sale, stock_low, review, etc.)"),
    )

    last_test_at = models.DateTimeField(null=True, blank=True)
    last_test_ok = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations"
        verbose_name = _("Integration")
        verbose_name_plural = _("Integrations")
        ordering = ["club_id", "type"]
        unique_together = [("club", "type")]

    def __str__(self):
        return f"{self.get_type_display()} for {self.club}"
