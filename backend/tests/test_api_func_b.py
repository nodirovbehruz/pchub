"""Functional-audit batch B regressions (timezone, order state, postpaid minutes)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone


# ── Server timezone must be the clubs' TZ (day/night tariffs + analytics) ────
def test_timezone_is_tashkent():
    from django.conf import settings
    assert settings.TIME_ZONE == "Asia/Tashkent"
    assert settings.USE_TZ is True


# ── An order cannot jump PENDING→COMPLETED (free goods without payment) ──────
@pytest.mark.django_db
def test_order_cannot_complete_without_payment(api, make_club, make_user):
    from apps.computers.models import Computer
    from apps.shops.models import Order
    club = make_club()
    pc = Computer.objects.create(name="PC-order-state", club=club)
    order = Order.objects.create(account=make_user(), computer=pc,
                                 total_price=Decimal("100"), status="PENDING")
    api.force_authenticate(user=club.owner)
    resp = api.post(f"/api/v1/shops/orders/admin/{order.id}/status/",
                    {"status": "COMPLETED"}, format="json")
    assert resp.status_code == 400
    order.refresh_from_db()
    assert order.status == "PENDING"  # not silently completed


# ── Closing a postpaid session must NOT wipe topped-up prepaid minutes ───────
@pytest.mark.django_db
def test_close_postpaid_keeps_prepaid_minutes(make_club, make_user, make_profile):
    from apps.billing.services.implementation.billing import BillingService
    club = make_club()
    client = make_user()
    prof = make_profile(
        client, club, session_mode="postpaid", minutes_remaining=30, is_active=True,
        postpaid_minutes=10, postpaid_rate=Decimal("60"),
        postpaid_started_at=timezone.now() - timedelta(minutes=10),
    )
    BillingService().close_postpaid_session(
        user_id=client.id, payment_method="cash", admin=club.owner, club_id=club.id)
    prof.refresh_from_db()
    assert prof.minutes_remaining == 30      # topped-up minutes preserved
    assert prof.session_mode == "prepaid"    # back to prepaid
