from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class PromocodeRewardType(models.TextChoices):
    DISCOUNT = "discount", _("Discount %")
    DEPOSIT_TOPUP = "deposit_topup", _("Top up deposit (money)")
    BONUS_TOPUP = "bonus_topup", _("Top up bonus balance")


class PromocodeChannel(models.TextChoices):
    ADMIN = "admin", _("Admin panel")
    MOBILE = "mobile", _("Mobile app")
    SHELL = "shell", _("Client shell")


class Promocode(models.Model):
    """One-time-per-client promotional code.

    SmartShell `/promo-codes`. Each client may use a promo only once.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="promocodes",
    )
    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120, blank=True, default="")

    reward_type = models.CharField(
        max_length=20,
        choices=PromocodeRewardType.choices,
        default=PromocodeRewardType.DISCOUNT,
    )
    value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"),
        help_text=_("Percent for DISCOUNT, money amount for DEPOSIT/BONUS topup"),
    )

    # Targeting
    client_group = models.ForeignKey(
        "clubs.ClientGroup",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="targeted_promocodes",
        help_text=_("If set — only members of this group; otherwise all clients"),
    )
    specific_clients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="targeted_promocodes",
        help_text=_("Specific clients only (if set, overrides group)"),
    )

    # Item scopes
    applies_to_tariffs = models.BooleanField(default=True)
    applies_to_products = models.BooleanField(default=True)
    applies_to_services = models.BooleanField(default=True)
    applies_to_combos = models.BooleanField(default=True)

    # Channels
    channels = models.JSONField(
        default=list,
        help_text=_("Allowed channels: ['admin','mobile','shell']"),
    )

    usage_limit = models.PositiveIntegerField(
        default=0,
        help_text=_("0 = unlimited"),
    )
    usage_count = models.PositiveIntegerField(default=0)

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    telegram_notify_on_use = models.BooleanField(default=False)
    telegram_notify_on_expire = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "loyalty_promocodes"
        verbose_name = _("Promocode")
        verbose_name_plural = _("Promocodes")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "is_active"]),
            models.Index(fields=["code"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_reward_type_display()})"

    @property
    def is_exhausted(self):
        return self.usage_limit > 0 and self.usage_count >= self.usage_limit


class PromocodeUsage(models.Model):
    """One-time use of a promocode by a client. Enforces «once per client»."""

    promocode = models.ForeignKey(
        Promocode,
        on_delete=models.CASCADE,
        related_name="usages",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="promocode_usages",
    )
    used_at = models.DateTimeField(auto_now_add=True)
    payment = models.ForeignKey(
        "billing.Payment",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="promocode_usages",
    )

    class Meta:
        db_table = "loyalty_promocode_usages"
        verbose_name = _("Promocode Usage")
        verbose_name_plural = _("Promocode Usages")
        unique_together = [("promocode", "client")]
        ordering = ["-used_at"]
