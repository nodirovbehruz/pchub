"""Achievement evaluation — unlocks achievements and applies their reward.

Was entirely missing: admins defined achievements and the shell showed an
"unlocked X/Y" badge, but no code ever created UserAchievement rows, so nothing
ever unlocked. Call evaluate_achievements(...) from the money/lifecycle hooks.
"""
from decimal import Decimal


def _apply_reward(profile, ach):
    """Apply an achievement reward to the client's per-club profile."""
    from apps.loyalty.models.achievement import RewardType
    if profile is None or not ach.reward_value:
        return
    try:
        if ach.reward_type == RewardType.DISCOUNT:
            # Raise the personal discount to at least the reward (never lower it).
            cur = profile.personal_discount or 0
            profile.personal_discount = max(int(cur), int(ach.reward_value))
            profile.save(update_fields=["personal_discount"])
        elif ach.reward_type == RewardType.BONUS:
            profile.bonus_balance = (profile.bonus_balance or Decimal("0")) + ach.reward_value
            profile.save(update_fields=["bonus_balance"])
    except Exception:
        pass


def evaluate_achievements(user, club_id, event, amount=Decimal("0")):
    """Unlock any newly-earned achievements for `user` in `club_id`.

    event: 'registration' | 'topup' | 'spend'
    amount: the current event's amount (for *_single / running totals).
    Best-effort and defensive — never raises into the caller's payment flow.
    """
    try:
        if not club_id:
            return
        from apps.loyalty.models import Achievement, UserAchievement
        from apps.loyalty.models.achievement import AchievementTrigger
        from apps.billing.services.implementation.billing import BillingService

        try:
            amount = Decimal(str(amount or 0))
        except Exception:
            amount = Decimal("0")

        achievements = list(Achievement.objects.filter(club_id=club_id, is_active=True))
        if not achievements:
            return
        already = set(
            UserAchievement.objects.filter(
                user=user, achievement__club_id=club_id
            ).values_list("achievement_id", flat=True)
        )
        profile = BillingService._get_profile(user, club_id)

        # Lazily-computed aggregates (only when a TOTAL/hours trigger needs them).
        totals = {}

        def topup_total():
            if "topup" not in totals:
                from apps.billing.models import Payment
                from django.db.models import Sum
                qs = (Payment.objects.filter(user=user, club_id=club_id)
                      .exclude(note__icontains="[POS]").exclude(note__icontains="[SHOP]")
                      .exclude(note__icontains="[REFUNDED]"))
                totals["topup"] = qs.aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")
            return totals["topup"]

        def spend_total():
            if "spend" not in totals:
                from apps.billing.models import Payment
                from django.db.models import Sum, Q
                qs = (Payment.objects.filter(user=user, club_id=club_id)
                      .filter(Q(note__icontains="[POS]") | Q(note__icontains="[SHOP]"))
                      .exclude(note__icontains="[REFUNDED]"))
                totals["spend"] = qs.aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")
            return totals["spend"]

        def hours_total():
            if "hours" not in totals:
                holder = profile or BillingService().get_or_create_user_balance(user)
                # Best-effort: purchased minutes as a proxy for time in club.
                from apps.billing.models import Payment
                from django.db.models import Sum
                mins = (Payment.objects.filter(user=user, club_id=club_id)
                        .aggregate(s=Sum("minutes_added"))["s"] or 0)
                totals["hours"] = Decimal(mins) / Decimal("60")
            return totals["hours"]

        T = AchievementTrigger
        to_unlock = []
        for ach in achievements:
            if ach.id in already:
                continue
            thr = ach.threshold or Decimal("0")
            hit = False
            if ach.trigger_type == T.REGISTRATION:
                hit = event == "registration"
            elif ach.trigger_type == T.TOPUP_SINGLE:
                hit = event == "topup" and amount >= thr
            elif ach.trigger_type == T.SPEND_SINGLE:
                hit = event == "spend" and amount >= thr
            elif ach.trigger_type == T.TOPUP_TOTAL:
                hit = event == "topup" and topup_total() >= thr
            elif ach.trigger_type == T.SPEND_TOTAL:
                hit = event == "spend" and spend_total() >= thr
            elif ach.trigger_type == T.HOURS_IN_CLUB:
                # Only evaluate on real activity events (not on every call).
                hit = event in ("topup", "spend") and hours_total() >= thr
            if hit:
                to_unlock.append(ach)

        for ach in to_unlock:
            _, created = UserAchievement.objects.get_or_create(achievement=ach, user=user)
            if created:
                _apply_reward(profile, ach)
    except Exception:
        # Never break the caller's payment/session flow on achievement errors.
        pass
