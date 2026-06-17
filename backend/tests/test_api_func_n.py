"""Regression for the deposit→hours flow: buying a tariff from the per-club DEPOSIT must
credit minutes to the PER-CLUB profile (which the shell plays from), NOT the legacy global
UserBalance — the historical "пополнил депозит, а часы не появились" bug."""
from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_buy_tariff_credits_per_club_not_global(api, make_club, make_user, make_profile):
    from apps.billing.models import TariffPlan, UserBalance
    from apps.clubs.models import UserClubProfile
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("100"), minutes_remaining=0)
    tariff = TariffPlan.objects.create(
        club=club, name="1 час", tariff_type="package", price=Decimal("50"), minutes=60)

    api.force_authenticate(user=client)
    resp = api.post(f"/api/v1/billing/client/buy-tariff/?club={club.id}",
                    {"tariff_id": tariff.id, "club": club.id}, format="json")
    assert resp.status_code == 200, resp.content

    prof = UserClubProfile.objects.get(user=client, club=club)
    assert prof.minutes_remaining == 60          # PLAYABLE per-club minutes credited
    assert prof.deposit_money == Decimal("50")   # 100 - 50

    bal = UserBalance.objects.filter(user=client).first()
    assert (bal.minutes_remaining if bal else 0) == 0  # global balance NOT touched


@pytest.mark.django_db
def test_buy_tariff_requires_club(api, make_club, make_user, make_profile):
    from apps.billing.models import TariffPlan
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("100"))
    tariff = TariffPlan.objects.create(
        club=club, name="X", tariff_type="package", price=Decimal("50"), minutes=60)
    api.force_authenticate(user=client)
    # No club anywhere → must 400, not silently credit the global balance.
    resp = api.post("/api/v1/billing/client/buy-tariff/", {"tariff_id": tariff.id}, format="json")
    assert resp.status_code == 400
