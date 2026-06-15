from django.db import models
from django.utils.translation import gettext_lazy as _


class Discount(models.Model):
    """Generic discount on tariff/product/service/combo.

    SmartShell `/discounts`. Applies only to items where 'use_global_discounts'
    (or 'applies_discount') is enabled.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="discounts",
    )
    name = models.CharField(_("Name"), max_length=120)
    percent = models.PositiveSmallIntegerField(
        _("Percent"),
        help_text=_("0..100 discount percent"),
    )

    schedule_days = models.CharField(
        max_length=7, default="1234567",
        help_text=_("Days when discount is active. 1=Mon..7=Sun"),
    )
    schedule_start = models.TimeField(null=True, blank=True)
    schedule_end = models.TimeField(null=True, blank=True)

    telegram_notify = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "loyalty_discounts"
        verbose_name = _("Discount")
        verbose_name_plural = _("Discounts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} −{self.percent}%"
