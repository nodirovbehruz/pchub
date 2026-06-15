from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class CashbackAccrualType(models.TextChoices):
    PERCENT = "percent", _("Percent")
    FIXED = "fixed", _("Fixed amount")


class CashbackRule(models.Model):
    """Cashback rule: «if client tops up >= threshold, give them N back».

    SmartShell `/cashback`:
    - Two rules cannot share the same threshold.
    - Promocodes are not counted toward threshold.
    - On topup refund the cashback is reversed.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="cashback_rules",
    )
    name = models.CharField(max_length=120, blank=True, default="")

    deposit_threshold = models.DecimalField(
        _("Topup threshold"),
        max_digits=12, decimal_places=2,
    )
    accrual_type = models.CharField(
        max_length=10,
        choices=CashbackAccrualType.choices,
        default=CashbackAccrualType.PERCENT,
    )
    value = models.DecimalField(
        _("Value"),
        max_digits=10, decimal_places=2,
        help_text=_("Percent (e.g. 5) or fixed money amount"),
    )

    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "loyalty_cashback_rules"
        verbose_name = _("Cashback Rule")
        verbose_name_plural = _("Cashback Rules")
        ordering = ["club_id", "deposit_threshold"]
        unique_together = [("club", "deposit_threshold")]

    def __str__(self):
        return f"Cashback {self.value}{'%' if self.accrual_type == CashbackAccrualType.PERCENT else 'сум'} @ ≥{self.deposit_threshold}"

    def compute_reward(self, topup_amount: Decimal) -> Decimal:
        if topup_amount < self.deposit_threshold:
            return Decimal("0")
        if self.accrual_type == CashbackAccrualType.PERCENT:
            return (topup_amount * self.value / Decimal("100")).quantize(Decimal("0.01"))
        return self.value
