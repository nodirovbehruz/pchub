"""B2B club billing — wallet top-up and subscription purchase from the wallet.

All money moves are atomic and write an immutable ledger row. The wallet never
goes negative.
"""

from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

PERIOD_DAYS = 30  # fixed monthly period (see ТЗ §12)
MAX_PREPAID_DAYS = 90  # max ~3 months prepaid; stops accidental click-stacking


def get_or_create_wallet(club):
    from apps.clubs.models import ClubWallet
    wallet, _ = ClubWallet.objects.get_or_create(club=club)
    return wallet


def _to_amount(value):
    """Parse a money amount into Decimal, raising a clean 400 on bad input
    (instead of a 500 from Decimal('None')/Decimal('abc')). Rejects NaN/Infinity —
    Decimal('NaN') silently passes `<= 0` / `< 0` guards and would poison the wallet."""
    from decimal import InvalidOperation
    if value is None or value == "":
        raise ValidationError({"amount": "Укажите сумму"})
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError({"amount": "Некорректная сумма"})
    if not amount.is_finite():
        raise ValidationError({"amount": "Некорректная сумма"})
    return amount


@transaction.atomic
def topup(club, amount, by_user=None, comment=""):
    """Super-admin credits the club's balance."""
    from apps.clubs.models import ClubWallet, ClubWalletTransaction, WalletTxnType
    amount = _to_amount(amount)
    if amount <= 0:
        raise ValidationError({"amount": "Сумма должна быть больше 0"})

    wallet = ClubWallet.objects.select_for_update().get_or_create(club=club)[0]
    wallet.balance += amount
    wallet.save(update_fields=["balance", "updated_at"])
    ClubWalletTransaction.objects.create(
        wallet=wallet, type=WalletTxnType.TOPUP, amount=amount,
        balance_after=wallet.balance, comment=comment, created_by=by_user,
    )
    return wallet


@transaction.atomic
def adjust(club, amount, by_user=None, comment=""):
    """Manual correction (can be negative). Never drives balance below 0."""
    from apps.clubs.models import ClubWallet, ClubWalletTransaction, WalletTxnType
    amount = _to_amount(amount)
    wallet = ClubWallet.objects.select_for_update().get_or_create(club=club)[0]
    new_balance = wallet.balance + amount
    if new_balance < 0:
        raise ValidationError({"amount": "Баланс не может стать отрицательным"})
    wallet.balance = new_balance
    wallet.save(update_fields=["balance", "updated_at"])
    ClubWalletTransaction.objects.create(
        wallet=wallet, type=WalletTxnType.ADJUST, amount=amount,
        balance_after=wallet.balance, comment=comment, created_by=by_user,
    )
    return wallet


@transaction.atomic
def buy_plan(club, plan, by_user=None):
    """Owner buys/renews a plan, paying monthly_price from the wallet. Activates the
    subscription for PERIOD_DAYS (extends, doesn't reset, an existing future expiry).
    Free plan (price 0) activates without charging."""
    from apps.clubs.models import (
        ClubWallet, ClubWalletTransaction, WalletTxnType,
        ClubSubscription, SubscriptionStatus,
    )
    price = Decimal(str(plan.monthly_price or 0))
    wallet = ClubWallet.objects.select_for_update().get_or_create(club=club)[0]

    existing = ClubSubscription.objects.filter(club=club).first()
    now = timezone.now()
    is_same_plan = bool(existing and existing.plan_id == plan.id)

    # Downgrade guard: can't move to a plan whose PC limit is below the club's
    # current active PC count (limit 0 = unlimited, always allowed).
    if plan.max_pcs and plan.max_pcs > 0:
        usage = pc_usage(club.id)
        if usage["used"] > plan.max_pcs:
            raise ValidationError({"plan": (
                f"На тарифе «{plan.name}» лимит {plan.max_pcs} ПК, а у клуба сейчас "
                f"{usage['used']}. Сначала отключите лишние ПК или выберите тариф побольше."
            )})

    # Prepay cap (absolute, regardless of plan): don't let click-stacking push the
    # expiry more than ~MAX_PREPAID_DAYS ahead. Only meaningful when extending the
    # SAME plan (switching starts a fresh period, see below).
    if (existing and is_same_plan and existing.expires_at
            and existing.expires_at > now + timedelta(days=MAX_PREPAID_DAYS)):
        raise ValidationError({"plan": (
            f"Тариф «{plan.name}» уже оплачен надолго вперёд "
            f"(до {existing.expires_at:%d.%m.%Y}). Продлевать пока не нужно."
        )})

    if price > 0:
        if wallet.balance < price:
            raise ValidationError(
                {"balance": f"Недостаточно средств: баланс {wallet.balance}, нужно {price}. Пополните баланс."}
            )
        wallet.balance -= price
        wallet.save(update_fields=["balance", "updated_at"])
        ClubWalletTransaction.objects.create(
            wallet=wallet, type=WalletTxnType.CHARGE, amount=-price,
            balance_after=wallet.balance, created_by=by_user,
            comment=f"Подписка «{plan.name}» на {PERIOD_DAYS} дн.",
        )

    sub, _ = ClubSubscription.objects.get_or_create(club=club, defaults={"plan": plan})
    # Same plan → extend from current (future) expiry. Switching plans → fresh
    # period from now (don't carry old plan's remaining days onto a new tier).
    base = sub.expires_at if (is_same_plan and sub.expires_at and sub.expires_at > now) else now
    sub.plan = plan
    sub.status = SubscriptionStatus.ACTIVE
    sub.expires_at = base + timedelta(days=PERIOD_DAYS)
    sub.save(update_fields=["plan", "status", "expires_at", "updated_at"])
    return sub, wallet


@transaction.atomic
def grant(club, plan, days=PERIOD_DAYS, by_user=None):
    """Super-admin grants/extends a subscription WITHOUT charging the wallet
    (bonus, trial extension, manual)."""
    from apps.clubs.models import ClubSubscription, SubscriptionStatus
    sub, _ = ClubSubscription.objects.get_or_create(club=club, defaults={"plan": plan})
    now = timezone.now()
    base = sub.expires_at if (sub.expires_at and sub.expires_at > now) else now
    sub.plan = plan
    sub.status = SubscriptionStatus.ACTIVE
    sub.expires_at = base + timedelta(days=int(days or PERIOD_DAYS))
    sub.save(update_fields=["plan", "status", "expires_at", "updated_at"])
    return sub


def _free_plan_max_pcs(default=5):
    """PC limit applied to clubs WITHOUT an active plan — falls back to the Free
    tier's limit (never 'unlimited', which is the bug we're fixing)."""
    from apps.clubs.models import SubscriptionPlan
    free = SubscriptionPlan.objects.filter(tier="free").first()
    if free and free.max_pcs and free.max_pcs > 0:
        return free.max_pcs
    return default


def pc_usage(club_id):
    """How many active PCs the club uses vs its plan limit. A plan's max_pcs of 0
    means unlimited; a club with NO subscription gets the Free-tier limit (NOT
    unlimited)."""
    from apps.computers.models import Computer
    from apps.clubs.models import ClubSubscription
    used = Computer.objects.filter(club_id=club_id, is_active=True).count()
    sub = ClubSubscription.objects.filter(club_id=club_id).select_related("plan").first()
    if sub and sub.plan:
        limit = sub.plan.max_pcs or 0  # 0 = unlimited for a real plan (e.g. Business)
        plan_name = sub.plan.name
    else:
        limit = _free_plan_max_pcs()    # no subscription → Free limit, not unlimited
        plan_name = None
    return {
        "used": used,
        "limit": limit,
        "plan": plan_name,
        "over": bool(limit and used > limit),
    }


def can_add_pc(club_id) -> bool:
    """True if the club may add one more PC under its current plan limit."""
    u = pc_usage(club_id)
    return u["limit"] == 0 or u["used"] < u["limit"]


def subscription_active(club) -> bool:
    """True if the club may use the platform (active or trial, not yet expired)."""
    from apps.clubs.models import ClubSubscription, SubscriptionStatus
    sub = ClubSubscription.objects.filter(club=club).select_related("plan").first()
    if not sub:
        return False
    now = timezone.now()
    if sub.status == SubscriptionStatus.TRIAL:
        # A trial with no end date is treated as ENDED (defensive) rather than infinite.
        return bool(club.trial_until) and now <= club.trial_until
    if sub.status == SubscriptionStatus.ACTIVE:
        # An ACTIVE row with no expiry is treated as NOT active (must have a real term).
        return bool(sub.expires_at) and now <= sub.expires_at
    # promised keeps access alive; expired/blocked → no access
    return sub.status == SubscriptionStatus.PROMISED
