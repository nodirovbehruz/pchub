"""Periodic subscription enforcement for clubs (Celery beat).

Runs daily and:
  1. Expires trials whose `trial_until` has passed → status EXPIRED.
  2. Blocks clubs whose promised-payment debt is overdue (due_at passed, unpaid)
     → subscription status BLOCKED.
  3. Downgrades clubs whose paid/promised subscription expired without renewal
     → status EXPIRED (free tier).

Schedule it in settings/celery.py beat_schedule, e.g.:
    "enforce-subscriptions": {
        "task": "apps.clubs.tasks.enforce_subscriptions",
        "schedule": 3600.0,   # hourly
    }
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="apps.clubs.tasks.enforce_subscriptions")
def enforce_subscriptions():
    from django.utils import timezone
    from apps.clubs.models import (
        Club, ClubSubscription, PromisedPayment, SubscriptionStatus,
    )

    now = timezone.now()
    stats = {"trials_expired": 0, "blocked_overdue": 0, "expired_subs": 0, "pcs_disabled": 0}

    def _disable_excess_pcs(club_id):
        # M7: buy_plan blocks a DOWNGRADE that exceeds the new PC limit, but an
        # AUTOMATIC expiry (trial/sub) demoted the plan without disabling excess PCs,
        # so a club could keep running 20 PCs on the Free (max 5) tier. Disable the
        # most-recently-added PCs beyond the now-applicable limit.
        try:
            from apps.clubs.services import billing as _bsvc
            from apps.computers.models import Computer
            u = _bsvc.pc_usage(club_id)
            used, limit = int(u.get("used") or 0), int(u.get("limit") or 0)
            if used > limit:
                excess = used - limit
                ids = list(Computer.objects.filter(club_id=club_id, is_active=True)
                           .order_by("-id").values_list("id", flat=True)[:excess])
                if ids:
                    Computer.objects.filter(id__in=ids).update(is_active=False)
                    stats["pcs_disabled"] += len(ids)
        except Exception:
            pass

    # 1. Expire trials whose trial_until has passed
    for sub in ClubSubscription.objects.filter(status=SubscriptionStatus.TRIAL).select_related("club"):
        club = sub.club
        if club.trial_until and now > club.trial_until:
            sub.status = SubscriptionStatus.EXPIRED
            sub.save(update_fields=["status"])
            stats["trials_expired"] += 1
            _disable_excess_pcs(club.id)

    # 2. Block clubs with overdue promised-payment debt
    overdue = (
        PromisedPayment.objects.filter(paid_at__isnull=True, due_at__lt=now)
        .select_related("subscription")
    )
    for pp in overdue:
        sub = pp.subscription
        if sub.status != SubscriptionStatus.BLOCKED:
            sub.status = SubscriptionStatus.BLOCKED
            sub.save(update_fields=["status"])
            stats["blocked_overdue"] += 1

    # 3. Expire active/promised subscriptions whose expires_at has passed
    #    (and there is no active promised payment keeping them alive)
    for sub in ClubSubscription.objects.filter(
        status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.PROMISED]
    ).select_related("club"):
        if sub.expires_at and now > sub.expires_at:
            has_open_promise = PromisedPayment.objects.filter(
                subscription=sub, paid_at__isnull=True, due_at__gte=now
            ).exists()
            if not has_open_promise:
                sub.status = SubscriptionStatus.EXPIRED
                sub.save(update_fields=["status"])
                stats["expired_subs"] += 1
                _disable_excess_pcs(sub.club_id)

    logger.info("enforce_subscriptions: %s", stats)
    return stats
