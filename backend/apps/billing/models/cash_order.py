from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CashOrderType(models.TextChoices):
    INCOME = "pko", _("Income (ПКО)")
    OUTCOME = "rko", _("Outcome (РКО)")


class CashOrder(models.Model):
    """Cash order — ПКО (income) or РКО (outcome) — tied to a Shift."""

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="cash_orders",
    )
    shift = models.ForeignKey(
        "billing.Shift",
        on_delete=models.CASCADE,
        related_name="cash_orders",
    )
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="cash_orders",
    )

    type = models.CharField(max_length=4, choices=CashOrderType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    comment = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cash_orders"
        verbose_name = _("Cash Order")
        verbose_name_plural = _("Cash Orders")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shift", "-created_at"]),
            models.Index(fields=["club", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()} {self.amount} ({self.club})"

    @property
    def signed_amount(self):
        """Positive for income, negative for outcome."""
        return self.amount if self.type == CashOrderType.INCOME else -self.amount
