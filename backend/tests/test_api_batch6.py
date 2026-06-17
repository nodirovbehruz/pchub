"""Batch 6 regression: refund of a bonus-paid deposit sale must not over-credit."""
from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_bonus_deposit_refund_splits_correctly(api, make_club, make_user, make_profile):
    """A deposit sale of 100 that spent 30 bonus + 70 deposit, when refunded, must
    return 70 to deposit and 30 to bonus — NOT 100 to deposit + 30 bonus (free money)."""
    from apps.billing.models import Payment
    club = make_club()
    client = make_user()
    prof = make_profile(client, club, deposit_money=Decimal("0"), bonus_balance=Decimal("0"))

    pay = Payment.objects.create(
        user=client, admin=club.owner, amount_paid=Decimal("100"),
        minutes_added=0, payment_method="deposit",
        note="[БОНУС 30]", club_id=club.id,
    )

    api.force_authenticate(user=club.owner)
    resp = api.post(f"/api/v1/billing/admin/payments/{pay.id}/refund/?club={club.id}",
                    {}, format="json")
    assert resp.status_code in (200, 201), resp.content

    prof.refresh_from_db()
    assert prof.deposit_money == Decimal("70")   # not 100
    assert prof.bonus_balance == Decimal("30")
    # Total value returned equals what was spent (100), not 130.
    assert prof.deposit_money + prof.bonus_balance == Decimal("100")
