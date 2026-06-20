"""Regression: selling a PREPAID fixed tariff to a GUEST must actually unlock the PC.
The shell auto-enters as guest-pc-<id> and reads ITS balance, so the bought minutes must
land on that guest profile — and guest-status must report active. Before, the payment
went through but the PC never unlocked ("деньги упали, комп не включился")."""
from decimal import Decimal
import pytest


@pytest.mark.django_db
def test_guest_prepaid_tariff_unlocks_pc(api, make_club):
    from apps.computers.models import Computer
    from apps.billing.models import TariffPlan
    from apps.clubs.models import UserClubProfile
    from apps.accounts.models import CustomUser

    club = make_club()
    pc = Computer.objects.create(club=club, hardware_id="HW-GP1", name="PC-1", is_active=True)
    tariff = TariffPlan.objects.create(name="1ч", minutes=60, price=Decimal("50000"), is_active=True)

    api.force_authenticate(user=club.owner)
    r = api.post("/api/v1/computers/admin/session/start/",
                 {"computer_id": pc.id, "user_id": None, "tariff_id": tariff.id,
                  "payment_method": "cash", "amount_paid": 50000},
                 format="json", HTTP_X_CLUB_ID=str(club.id))
    assert r.status_code == 200, r.content

    guest = CustomUser.objects.get(username=f"guest-pc-{pc.id}")
    prof = UserClubProfile.objects.get(user=guest, club_id=club.id)
    assert prof.minutes_remaining == 60, f"guest got {prof.minutes_remaining} min"
    assert prof.is_active and prof.is_guest

    # Public guest-status poll (what the shell hits) must now report active → unlock.
    s = api.get("/api/v1/billing/guest/status/?hardware_id=HW-GP1")
    assert s.status_code == 200, s.content
    assert s.json().get("active") is True, s.content
