from django.db import models
from django.utils.translation import gettext_lazy as _


class TariffType(models.TextChoices):
    FIXED = "fixed", _("Fixed (e.g. 1 hour)")
    PACKAGE = "package", _("Package (e.g. Night pack)")
    PER_MINUTE = "per_minute", _("Per minute")
    SUBSCRIPTION = "subscription", _("Subscription / Abonement")


class TariffPlan(models.Model):
    """Tariff offered to clients. Supports 4 types matching SmartShell.

    - FIXED: a fixed-length block (1h, 3h, 5h)
    - PACKAGE: time-bounded block ("Night pack" — until 08:00)
    - PER_MINUTE: pay-as-you-play, 1 minute granularity
    - SUBSCRIPTION: bulk hours that live for `life_days`
    """

    name = models.CharField(max_length=100, verbose_name=_("Name"))

    tariff_type = models.CharField(
        max_length=20,
        choices=TariffType.choices,
        default=TariffType.FIXED,
        verbose_name=_("Tariff type"),
    )

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="tariffs",
        verbose_name=_("Club"),
        help_text=_("Club this tariff belongs to. Null = legacy/global."),
    )

    # Base price kept for backward compatibility and as a fallback
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Base price"),
        help_text=_("Fallback price if no per-zone TariffPrice rows exist"),
    )

    minutes = models.PositiveIntegerField(
        default=60,
        verbose_name=_("Duration (minutes)"),
        help_text=_("Granted minutes. For per_minute use 1. For package — until valid_until_time."),
    )

    valid_until_time = models.TimeField(
        null=True, blank=True,
        verbose_name=_("Valid until (time)"),
        help_text=_("For PACKAGE: explicit end-of-validity (e.g. 08:00)"),
    )

    life_days = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Life span (days)"),
        help_text=_("For SUBSCRIPTION: how many days the bought tariff stays valid"),
    )

    # Schedule of *when this tariff is active* (e.g. Night Pack works 22:00–08:00)
    schedule_days = models.CharField(
        max_length=7,
        default="1234567",
        verbose_name=_("Active days"),
        help_text=_("Days of week the tariff is active. 1=Mon … 7=Sun"),
    )
    schedule_start = models.TimeField(
        null=True, blank=True,
        verbose_name=_("Schedule start"),
    )
    schedule_end = models.TimeField(
        null=True, blank=True,
        verbose_name=_("Schedule end"),
    )

    # Flags shown as small icons on tariff card
    is_night = models.BooleanField(default=False, verbose_name=_("Night tariff"))
    apply_discount = models.BooleanField(default=True, verbose_name=_("Discounts applicable"))
    has_schedule = models.BooleanField(default=False, verbose_name=_("Has schedule restriction"))

    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        db_table = "billing_tariff_plans"
        verbose_name = _("Tariff Plan")
        verbose_name_plural = _("Tariff Plans")
        ordering = ["club_id", "tariff_type", "price"]

    def __str__(self):
        return f"{self.name} ({self.get_tariff_type_display()})"

    @property
    def hours_display(self) -> str:
        if self.tariff_type == TariffType.PER_MINUTE:
            return "1 мин"
        if self.tariff_type == TariffType.PACKAGE and self.valid_until_time:
            return f"до {self.valid_until_time.strftime('%H:%M')}"
        h = self.minutes // 60
        m = self.minutes % 60
        if h > 0 and m > 0:
            return f"{h}ч {m}м"
        elif h > 0:
            return f"{h} ч"
        return f"{self.minutes} мин"

    @property
    def days_label(self) -> str:
        """Render schedule_days as human-readable badges (Пн, Вт, ...)."""
        names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        chars = [c for c in (self.schedule_days or "") if c.isdigit()]
        days = sorted({int(c) for c in chars if 1 <= int(c) <= 7})
        return ", ".join(names[d - 1] for d in days)


class PricePeriod(models.TextChoices):
    DAY = "day", _("Day")
    NIGHT = "night", _("Night")


class TariffPrice(models.Model):
    """Per-zone + per-period price for a TariffPlan.

    Example for "Абонемент 5 часов":
      - Main Zone / Day: 1000сум
      - Main Zone / Night: 900сум
      - VIP Lounge / Day: 1200сум
      - VIP Lounge / Night: 1000сум
    """

    tariff = models.ForeignKey(
        TariffPlan,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    group = models.ForeignKey(
        "computers.ComputerGroup",
        on_delete=models.CASCADE,
        related_name="tariff_prices",
        verbose_name=_("Computer group / zone"),
    )
    period = models.CharField(
        max_length=10,
        choices=PricePeriod.choices,
        default=PricePeriod.DAY,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "billing_tariff_prices"
        verbose_name = _("Tariff Price")
        verbose_name_plural = _("Tariff Prices")
        unique_together = [("tariff", "group", "period")]
        ordering = ["tariff_id", "group_id", "period"]

    def __str__(self):
        return f"{self.tariff.name} / {self.group.name} / {self.period}: {self.price}"
