from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserBalance(models.Model):
    """Legacy global user balance.

    Note: per-club deposit/bonus/discount are now stored in
    `apps.clubs.UserClubProfile`. This model is kept for backward
    compatibility with the legacy minutes-based flow and for global flags.

    session_mode:
      'prepaid'  — client must have minutes_remaining > 0 to play (default)
      'postpaid' — client plays first, pays when leaving; debt tracked in
                   postpaid_minutes; is_active stays True during session.
    """

    SESSION_PREPAID  = "prepaid"
    SESSION_POSTPAID = "postpaid"
    SESSION_CHOICES  = [
        ("prepaid",  "Предоплата"),
        ("postpaid", "Постоплата"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="balance",
        verbose_name=_("User"),
    )
    minutes_remaining = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Minutes Remaining"),
        help_text=_("Legacy free minutes counter. Prefer UserClubProfile.deposit_money."),
    )
    deposit_money = models.DecimalField(
        _("Deposit (money, global fallback)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Optional global deposit. Per-club deposit lives in UserClubProfile."),
    )
    bonus_balance = models.DecimalField(
        _("Bonus balance (global fallback)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
    )
    is_active = models.BooleanField(
        default=False,
        verbose_name=_("Is Active"),
    )

    # ── Postpaid fields ───────────────────────────────────────────────────────
    session_mode = models.CharField(
        max_length=10,
        choices=SESSION_CHOICES,
        default=SESSION_PREPAID,
        verbose_name=_("Session mode"),
    )
    postpaid_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Postpaid minutes (debt)"),
        help_text=_("Minutes played on credit in the current postpaid session."),
    )
    postpaid_started_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Postpaid session started at"),
    )
    postpaid_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_("Postpaid rate (сум/hour)"),
        help_text=_("Hourly rate used when closing the postpaid session."),
    )

    last_updated = models.DateTimeField(auto_now=True, verbose_name=_("Last Updated"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        db_table = "billing_user_balance"
        verbose_name = _("User Balance")
        verbose_name_plural = _("User Balances")
        ordering = ["user__username"]

    def __str__(self):
        if self.session_mode == self.SESSION_POSTPAID:
            return f"{self.user.username} — постоплата {self.postpaid_minutes} мин."
        return f"{self.user.username} — {self.minutes_remaining} мин."

    @property
    def hours_remaining(self) -> float:
        return round(self.minutes_remaining / 60, 2)

    @property
    def formatted_time(self) -> str:
        h = self.minutes_remaining // 60
        m = self.minutes_remaining % 60
        return f"{h:02d}:{m:02d}"

    @property
    def postpaid_amount_due(self) -> Decimal:
        """Calculated cost for the current postpaid session."""
        if not self.postpaid_rate:
            return Decimal("0")
        hours = Decimal(str(self.postpaid_minutes)) / Decimal("60")
        return (self.postpaid_rate * hours).quantize(Decimal("0.01"))

    def add_minutes(self, minutes: int) -> None:
        self.minutes_remaining += minutes
        self.is_active = True
        self.save(update_fields=["minutes_remaining", "is_active", "last_updated"])

    def deduct_minute(self) -> bool:
        """Deduct one minute. In postpaid mode, increments the debt instead."""
        if self.session_mode == self.SESSION_POSTPAID:
            # Count upward — client plays on credit
            self.postpaid_minutes += 1
            self.is_active = True
            self.save(update_fields=["postpaid_minutes", "is_active", "last_updated"])
            return True  # always has access during postpaid session

        # Prepaid logic
        if self.minutes_remaining > 0:
            self.minutes_remaining -= 1
            if self.minutes_remaining == 0:
                self.is_active = False
            self.save(update_fields=["minutes_remaining", "is_active", "last_updated"])
            return self.minutes_remaining > 0
        self.is_active = False
        self.save(update_fields=["is_active", "last_updated"])
        return False
