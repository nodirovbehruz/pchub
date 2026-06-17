"""Regression for the CRITICAL: refunding a combined (time+money) topup must DEBIT
the deposit it credited — was kept by the client (free money) because the refund keyed
off minutes_added==0 and a combined topup has minutes>0."""
from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_combined_topup_refund_debits_deposit(api, make_club, make_user, make_profile):
    from apps.billing.services.implementation.billing import BillingService
    from apps.billing.models import Payment
    from apps.clubs.models import UserClubProfile
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("0"), minutes_remaining=0)

    # Combined topup: 60 minutes + 100 money, cash.
    BillingService().topup_user(
        user_id=client.id, minutes=60, amount_paid=Decimal("100"),
        payment_method="cash", admin=club.owner, club_id=club.id)

    prof = UserClubProfile.objects.get(user=client, club=club)
    assert prof.deposit_money == Decimal("100")           # topup credited deposit
    pay = Payment.objects.filter(user=client, club_id=club.id).order_by("-id").first()
    assert "[TOPUP]" in (pay.note or "")                   # marker stamped

    api.force_authenticate(user=club.owner)
    resp = api.post(f"/api/v1/billing/admin/payments/{pay.id}/refund/?club={club.id}",
                    {}, format="json")
    assert resp.status_code in (200, 201), resp.content

    prof.refresh_from_db()
    assert prof.deposit_money == Decimal("0")              # deposit debited back (the fix)
