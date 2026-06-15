from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ClubWallet(models.Model):
    """B2B wallet: the club's balance with the PLATFORM (used to pay for the
    subscription). Topped up manually by the super-admin via /platform. Distinct
    from a client's per-club deposit (that's the B2C wallet)."""

    club = models.OneToOneField(
        "clubs.Club", on_delete=models.CASCADE, related_name="wallet",
    )
    balance = models.DecimalField(
        _("Balance"), max_digits=12, decimal_places=2, default=Decimal("0"),
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "club_wallets"
        verbose_name = _("Club Wallet")
        verbose_name_plural = _("Club Wallets")

    def __str__(self):
        return f"{self.club} — {self.balance}"


class WalletTxnType(models.TextChoices):
    TOPUP = "topup", _("Top-up")        # super-admin credited the balance
    CHARGE = "charge", _("Subscription charge")  # plan purchase/renewal
    REFUND = "refund", _("Refund")
    ADJUST = "adjust", _("Manual adjustment")


class ClubWalletTransaction(models.Model):
    """Immutable ledger of every wallet movement (audit + reporting/MRR)."""

    wallet = models.ForeignKey(
        ClubWallet, on_delete=models.CASCADE, related_name="transactions",
    )
    type = models.CharField(max_length=12, choices=WalletTxnType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)  # +credit / −debit
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    comment = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="club_wallet_txns",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "club_wallet_transactions"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["wallet", "created_at"])]

    def __str__(self):
        return f"{self.type} {self.amount} → {self.balance_after}"
