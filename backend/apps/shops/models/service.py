from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class Service(models.Model):
    """Standalone service (e.g. printing, equipment repair) — not stock-tracked.

    SmartShell distinguishes Goods (склад) and Services (без склада).
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="services",
    )
    name = models.CharField(_("Name"), max_length=50)
    price = models.DecimalField(
        _("Price"),
        max_digits=10, decimal_places=3,
        default=Decimal("0"),
        help_text=_("0..999999, up to 3 decimal places"),
    )
    barcode = models.CharField(
        _("Barcode"), max_length=13, blank=True, default="",
    )
    description = models.TextField(blank=True, default="")
    applies_discount = models.BooleanField(
        _("Applies discount"), default=True,
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shop_services"
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        ordering = ["club_id", "name"]
        indexes = [
            models.Index(fields=["club", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.price}сум)"
