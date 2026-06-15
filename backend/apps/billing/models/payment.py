from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .enums import PaymentMethod


class Payment(models.Model):
    """Records each payment/top-up made by an admin for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("User"),
        null=True,
        blank=True,
    )
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.SET_NULL,
        related_name="computer_payments",
        verbose_name=_("Computer"),
        null=True,
        blank=True,
        help_text=_("Legacy field — computer where session was played"),
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="billing_payments",
        verbose_name=_("Admin"),
        help_text=_("Admin who processed this payment"),
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Amount Paid"),
        help_text=_("Monetary amount received"),
    )
    minutes_added = models.PositiveIntegerField(
        verbose_name=_("Minutes Added"),
        help_text=_("Play time granted in minutes"),
    )
    payment_method = models.CharField(
        max_length=20,
        choices=[
            (PaymentMethod.CASH, _("Наличные")),
            (PaymentMethod.CARD, _("Карта")),
            (PaymentMethod.TRANSFER, _("Перевод")),
        ],
        default=PaymentMethod.CASH,
        verbose_name=_("Payment Method"),
    )
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="payments",
        verbose_name=_("Club"),
        help_text=_("Club where this payment was made"),
    )
    note = models.TextField(blank=True, verbose_name=_("Note"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "billing_payments"
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["computer"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        name = (
            self.user.username
            if self.user
            else (self.computer.name if self.computer else "—")
        )
        return f"{name} | {self.minutes_added} мин. | {self.amount_paid}"


class AnalyticsMetrics(Payment):
    class Meta:
        proxy = True
        verbose_name = _("🔍 Аналитика")
        verbose_name_plural = _("🔍 Аналитика")
