"""Regression: analytics REVENUE must exclude deposit-funded purchases.

A tariff/shop item bought FROM a client's deposit (payment_method="deposit", or an internal
"[DEPOSIT]"-marked transfer) is NOT new revenue — the money was already counted when the
client topped up. Counting it again double-counts and produced 'unreal' revenue figures.
Consumption/spending breakdowns legitimately still include deposit-funded buys."""
from decimal import Decimal

import pytest


def _mk_payments(club, client):
    from apps.billing.models import Payment
    # REAL money in (counts as revenue):
    Payment.objects.create(user=client, club=club, amount_paid=Decimal("150000"),
                           minutes_added=0, payment_method="cash", note="[TOPUP]")
    Payment.objects.create(user=client, club=club, amount_paid=Decimal("3000"),
                           minutes_added=0, payment_method="transfer", note="[POS] кола")
    # NOT revenue — deposit-funded buys (already counted at top-up):
    Payment.objects.create(user=client, club=club, amount_paid=Decimal("10000"),
                           minutes_added=60, payment_method="deposit", note="[CLIENT] Тариф: 1 час")
    Payment.objects.create(user=client, club=club, amount_paid=Decimal("5000"),
                           minutes_added=0, payment_method="transfer", note="[DEPOSIT][POS] чипсы")


@pytest.mark.django_db
def test_overview_revenue_excludes_deposit_funded(api, make_club, make_user):
    club = make_club()
    client = make_user()
    _mk_payments(club, client)

    api.force_authenticate(user=club.owner)
    resp = api.get(f"/api/v1/billing/analytics/?club={club.id}&from=2020-01-01&to=2030-12-31")
    assert resp.status_code == 200, resp.content
    data = resp.json()

    # 150000 cash + 3000 real transfer = 153000. The 10000 deposit buy and 5000
    # [DEPOSIT] transfer are EXCLUDED (would have inflated it to 168000).
    assert data["financial"]["revenue"] == 153000.0
    assert data["revenue_by_method"]["total"] == 153000.0
    assert data["revenue_by_method"]["cash"] == 150000.0
    assert data["revenue_by_method"]["online"] == 3000.0          # [DEPOSIT] transfer dropped
    assert data["revenue_by_method"]["deposit"] == 10000.0        # shown as info, not in total


@pytest.mark.django_db
def test_dashboard_tariffs_revenue_excludes_deposit(api, make_club, make_user):
    from apps.billing.models import Payment
    club = make_club()
    client = make_user()
    # Direct cash tariff sale = revenue; deposit-funded tariff buy = not revenue.
    Payment.objects.create(user=client, club=club, amount_paid=Decimal("12000"),
                           minutes_added=60, payment_method="cash", note="Тариф касса")
    Payment.objects.create(user=client, club=club, amount_paid=Decimal("10000"),
                           minutes_added=60, payment_method="deposit", note="[CLIENT] Тариф: 1 час")

    api.force_authenticate(user=club.owner)
    resp = api.get(f"/api/v1/billing/dashboard/?club={club.id}")
    assert resp.status_code == 200, resp.content
    data = resp.json()
    cat = data.get("revenue_by_category", {})
    assert Decimal(str(cat.get("tariffs"))) == Decimal("12000")   # deposit buy excluded
