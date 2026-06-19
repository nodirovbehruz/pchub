"""Regression for the 'logged in with money but no time' flow.

A client who has deposit money but 0 minutes must NOT be treated as 'balance ended'
(which makes the shell kick them to login). The balance endpoint must expose the deposit
and a `can_buy_tariff` flag so the shell can open the tariffs screen and let them convert
money → minutes themselves. has_access stays False (they can't PLAY until they buy)."""
from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_balance_signals_can_buy_when_deposit_covers_a_tariff(api, make_club, make_user, make_profile):
    from apps.billing.models import TariffPlan
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("100"), minutes_remaining=0)
    TariffPlan.objects.create(
        club=club, name="1 час", tariff_type="package", price=Decimal("50"), minutes=60)

    api.force_authenticate(user=client)
    resp = api.get(f"/api/v1/billing/balance/?club={club.id}")
    assert resp.status_code == 200, resp.content
    data = resp.json()

    assert data["has_access"] is False            # 0 minutes → still can't PLAY
    assert data["can_buy_tariff"] is True         # but deposit 100 >= cheapest tariff 50
    assert Decimal(data["deposit_money"]) == Decimal("100")  # exposed to the shell


@pytest.mark.django_db
def test_balance_cannot_buy_when_deposit_below_cheapest(api, make_club, make_user, make_profile):
    from apps.billing.models import TariffPlan
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("10"), minutes_remaining=0)
    TariffPlan.objects.create(
        club=club, name="1 час", tariff_type="package", price=Decimal("50"), minutes=60)

    api.force_authenticate(user=client)
    resp = api.get(f"/api/v1/billing/balance/?club={club.id}")
    assert resp.status_code == 200, resp.content
    data = resp.json()

    assert data["has_access"] is False
    assert data["can_buy_tariff"] is False        # deposit 10 < cheapest tariff 50


@pytest.mark.django_db
def test_balance_no_can_buy_when_already_has_time(api, make_club, make_user, make_profile):
    from apps.billing.models import TariffPlan
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("100"), minutes_remaining=30, is_active=True)
    TariffPlan.objects.create(
        club=club, name="1 час", tariff_type="package", price=Decimal("50"), minutes=60)

    api.force_authenticate(user=client)
    resp = api.get(f"/api/v1/billing/balance/?club={club.id}")
    assert resp.status_code == 200, resp.content
    data = resp.json()

    assert data["has_access"] is True             # has minutes → can play
    assert data["can_buy_tariff"] is False        # not prompted to buy while already playing
