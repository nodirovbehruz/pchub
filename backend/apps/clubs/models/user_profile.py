from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserClubProfile(models.Model):
    """Per-club profile of a client.

    SmartShell: «База клиентов единая, но в каждом клубе у клиента свои условия:
    депозит, бонусный баланс, скидка». This model holds those per-club values.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="club_profiles",
    )
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="user_profiles",
    )

    deposit_money = models.DecimalField(
        _("Deposit (money)"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Real money on the deposit, in club currency"),
    )
    bonus_balance = models.DecimalField(
        _("Bonus balance"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Bonus credits earned via cashback/promocodes"),
    )

    # ── Per-club playable time & session (new billing model) ───────────────────
    # Money/wallet is global (UserBalance.deposit_money); TIME is bought at the
    # club and lives here so it can't be carried to another club.
    SESSION_PREPAID = "prepaid"
    SESSION_POSTPAID = "postpaid"
    SESSION_CHOICES = [("prepaid", "Предоплата"), ("postpaid", "Постоплата")]

    minutes_remaining = models.PositiveIntegerField(
        _("Minutes remaining (this club)"),
        default=0,
        help_text=_("Playable minutes purchased at THIS club."),
    )
    is_active = models.BooleanField(_("Session active"), default=False)
    session_mode = models.CharField(
        max_length=10, choices=SESSION_CHOICES, default=SESSION_PREPAID,
        verbose_name=_("Session mode"),
    )
    postpaid_minutes = models.PositiveIntegerField(
        _("Postpaid minutes (debt)"), default=0,
        help_text=_("Minutes played on credit in the current postpaid session."),
    )
    postpaid_started_at = models.DateTimeField(_("Postpaid started at"), null=True, blank=True)
    postpaid_rate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name=_("Postpaid rate (per hour)"),
    )
    # Guest postpaid: a walk-in session started by the operator on a PC without a
    # registered client account (see planned guest-postpaid flow).
    is_guest = models.BooleanField(
        _("Guest session"), default=False,
        help_text=_("True when this profile is an anonymous walk-in (no real client)."),
    )

    personal_discount = models.PositiveSmallIntegerField(
        _("Personal discount %"),
        default=0,
        help_text=_("0..100 — overrides group discount if both set (max wins)"),
    )
    group = models.ForeignKey(
        "clubs.ClientGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
    )

    is_blocked = models.BooleanField(default=False)
    comment = models.TextField(blank=True, default="")
    important_comment = models.BooleanField(
        default=False,
        help_text=_("If true, comment is highlighted in sale dialog"),
    )

    last_visit_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_club_profiles"
        verbose_name = _("User Club Profile")
        verbose_name_plural = _("User Club Profiles")
        unique_together = [("user", "club")]
        ordering = ["-last_visit_at"]

    def __str__(self):
        return f"{self.user} @ {self.club} (сум{self.deposit_money})"

    @property
    def effective_discount(self):
        """Returns max(personal, group.percent_discount)."""
        group_discount = self.group.percent_discount if self.group else 0
        return max(self.personal_discount, group_discount)

    # ── Per-club time helpers (mirror legacy UserBalance, scoped to club) ──────
    @property
    def formatted_time(self) -> str:
        h = self.minutes_remaining // 60
        m = self.minutes_remaining % 60
        return f"{h:02d}:{m:02d}"

    @property
    def postpaid_amount_due(self) -> Decimal:
        if not self.postpaid_rate:
            return Decimal("0")
        hours = Decimal(str(self.postpaid_minutes)) / Decimal("60")
        return (self.postpaid_rate * hours).quantize(Decimal("0.01"))

    def add_minutes(self, minutes: int) -> None:
        self.minutes_remaining += minutes
        self.is_active = True
        self.save(update_fields=["minutes_remaining", "is_active", "updated_at"])

    def deduct_minute(self) -> bool:
        """Deduct one minute at this club. Postpaid → accrues debt instead.

        Row-locked: two concurrent per-minute pings used to read the same value and
        clobber each other's write (lost minute counts / undercharged postpaid).
        """
        from django.db import transaction
        cls = type(self)
        with transaction.atomic():
            locked = cls.objects.select_for_update().get(pk=self.pk)
            if locked.session_mode == self.SESSION_POSTPAID:
                new_pp = (locked.postpaid_minutes or 0) + 1
                cls.objects.filter(pk=self.pk).update(postpaid_minutes=new_pp, is_active=True)
                self.postpaid_minutes = new_pp
                self.is_active = True
                return True
            if locked.minutes_remaining > 0:
                new_val = locked.minutes_remaining - 1
                cls.objects.filter(pk=self.pk).update(
                    minutes_remaining=new_val, is_active=(new_val > 0))
                self.minutes_remaining = new_val
                self.is_active = new_val > 0
                return new_val > 0
            cls.objects.filter(pk=self.pk).update(is_active=False)
            self.is_active = False
            return False
