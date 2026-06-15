from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Combo(models.Model):
    """Combo-set: optional tariff + multiple products/services at a reduced price.

    SmartShell rules:
    - At most one tariff (FIXED or PACKAGE; price cannot be lowered)
    - Multiple products (price in combo can be lowered; combo qty = min product stock)
    - Multiple services (price in combo can be lowered)
    - Requires ComputerGroup if a tariff is included (different prices per zone)
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="combos",
    )
    name = models.CharField(max_length=50)

    computer_group = models.ForeignKey(
        "computers.ComputerGroup",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="combos",
        help_text=_("Required if tariff is set (combo price depends on zone)"),
    )
    tariff = models.ForeignKey(
        "billing.TariffPlan",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="combos",
    )

    base_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text=_("Calculated from constituent items at full price"),
    )
    sale_price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text=_("Combo selling price (discounted)"),
    )
    applies_discount = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shop_combos"
        verbose_name = _("Combo")
        verbose_name_plural = _("Combos")
        ordering = ["club_id", "name"]

    def __str__(self):
        return f"{self.name} ({self.sale_price}сум)"


class ComboProductItem(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name="product_items")
    product = models.ForeignKey("shops.Product", on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)
    price_in_combo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "shop_combo_product_items"
        unique_together = [("combo", "product")]


class ComboServiceItem(models.Model):
    combo = models.ForeignKey(Combo, on_delete=models.CASCADE, related_name="service_items")
    service = models.ForeignKey("shops.Service", on_delete=models.CASCADE)
    qty = models.PositiveIntegerField(default=1)
    price_in_combo = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "shop_combo_service_items"
        unique_together = [("combo", "service")]
