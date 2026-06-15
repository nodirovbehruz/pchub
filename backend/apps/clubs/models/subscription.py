from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class SubscriptionPlan(models.Model):
    """Platform-level subscription plan: Free / Starter / Business."""

    class Tier(models.TextChoices):
        FREE = "free", _("Free")
        STARTER = "starter", _("Starter")
        BUSINESS = "business", _("Business")

    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    name = models.CharField(max_length=120)
    monthly_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"),
    )
    max_pcs = models.PositiveIntegerField(
        default=0,
        help_text=_("0 = unlimited; limit applied to total active Computer count per club"),
    )
    features = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subscription_plans"
        verbose_name = _("Subscription Plan")
        verbose_name_plural = _("Subscription Plans")
        ordering = ["monthly_price"]

    def __str__(self):
        return self.name


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    TRIAL = "trial", _("Trial")
    PROMISED = "promised", _("Promised payment")
    EXPIRED = "expired", _("Expired (Free)")
    BLOCKED = "blocked", _("Blocked (>37 days unpaid)")


class ClubSubscription(models.Model):
    """A club's active subscription record."""

    club = models.OneToOneField(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="club_subscriptions",
    )
    status = models.CharField(
        max_length=12, choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.TRIAL,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    auto_renew = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "club_subscriptions"
        verbose_name = _("Club Subscription")
        verbose_name_plural = _("Club Subscriptions")
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.club} → {self.plan.name} [{self.status}]"


class PromisedPayment(models.Model):
    """7-day grace period on subscription payment.

    SmartShell rules:
    - Fixed fee 500 сум
    - Only for clubs that have previously paid for subscription
    - 7 days to pay → otherwise downgrade to Free
    - 37 days unpaid → club blocked
    """

    subscription = models.ForeignKey(
        ClubSubscription,
        on_delete=models.CASCADE,
        related_name="promised_payments",
    )
    fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("500"),
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "promised_payments"
        verbose_name = _("Promised Payment")
        verbose_name_plural = _("Promised Payments")
        ordering = ["-granted_at"]

    def __str__(self):
        status = "paid" if self.paid_at else f"due {self.due_at:%Y-%m-%d}"
        return f"Promised {self.fee_amount}сум — {status}"
