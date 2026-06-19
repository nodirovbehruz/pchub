"""Regression: the LIVE shift cash register (header «Касса») must include manual cash
orders — ПКО (income) add to the drawer, РКО (outcome) remove — exactly like the
close-shift discrepancy already does. Before, _shift_realtime returned only
initial+cash_revenue and ignored orders, so a 4M РКО didn't reduce the till."""
from datetime import timedelta
from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_live_cash_register_includes_manual_orders(api, make_club, make_user):
    from django.utils import timezone
    from apps.billing.models import Shift, Payment, CashOrder, CashOrderType
    club = make_club()
    owner = club.owner
    buyer = make_user()
    shift = Shift.objects.create(
        club=club, admin=owner, initial_cash=Decimal("1000"),
        is_active=True, start_time=timezone.now() - timedelta(hours=1))
    Payment.objects.create(user=buyer, club=club, amount_paid=Decimal("500"),
                           minutes_added=0, payment_method="cash")
    CashOrder.objects.create(club=club, shift=shift, type=CashOrderType.INCOME, amount=Decimal("300"))
    CashOrder.objects.create(club=club, shift=shift, type=CashOrderType.OUTCOME, amount=Decimal("200"))

    api.force_authenticate(user=owner)
    resp = api.get(f"/api/v1/billing/shifts/current/?club={club.id}")
    assert resp.status_code == 200, resp.content
    s = resp.json()["shift"]
    # Касса = 1000 initial + 500 cash + 300 ПКО − 200 РКО = 1600
    assert Decimal(s["expected_cash"]) == Decimal("1600")
    assert Decimal(s["manual_cash_orders"]) == Decimal("100")
