"""Guest PREPAID fixed-tariff lifecycle through the shell-facing endpoints:
  • START credits minutes to guest-pc-<id> → guest-status active → PC unlocks.
  • STOP zeroes that profile → guest-status inactive → shell LOCKS.
Before, START left the PC locked and STOP left the shell playing."""
from decimal import Decimal
import pytest


def _setup(make_club, hw):
    from apps.computers.models import Computer
    from apps.billing.models import TariffPlan
    club = make_club()
    pc = Computer.objects.create(club=club, hardware_id=hw, name="PC", is_active=True)
    tariff = TariffPlan.objects.create(name="1ч", minutes=60, price=Decimal("50000"), is_active=True)
    return club, pc, tariff


def _start(api, club, pc, tariff):
    return api.post("/api/v1/computers/admin/session/start/",
                    {"computer_id": pc.id, "user_id": None, "tariff_id": tariff.id,
                     "payment_method": "cash", "amount_paid": 50000},
                    format="json", HTTP_X_CLUB_ID=str(club.id))


@pytest.mark.django_db
def test_guest_prepaid_start_unlocks(api, make_club):
    from apps.clubs.models import UserClubProfile
    from apps.accounts.models import CustomUser
    club, pc, tariff = _setup(make_club, "HW-GP1")
    api.force_authenticate(user=club.owner)
    assert _start(api, club, pc, tariff).status_code == 200
    prof = UserClubProfile.objects.get(user=CustomUser.objects.get(username=f"guest-pc-{pc.id}"), club_id=club.id)
    assert prof.minutes_remaining == 60 and prof.is_active and prof.is_guest
    assert api.get("/api/v1/billing/guest/status/?hardware_id=HW-GP1").json().get("active") is True


@pytest.mark.django_db
def test_guest_prepaid_stop_locks(api, make_club):
    from apps.clubs.models import UserClubProfile
    from apps.accounts.models import CustomUser
    club, pc, tariff = _setup(make_club, "HW-GP2")
    api.force_authenticate(user=club.owner)
    _start(api, club, pc, tariff)
    r = api.post("/api/v1/computers/admin/session/stop/",
                 {"computer_id": pc.id}, format="json", HTTP_X_CLUB_ID=str(club.id))
    assert r.status_code == 200, r.content
    prof = UserClubProfile.objects.get(user=CustomUser.objects.get(username=f"guest-pc-{pc.id}"), club_id=club.id)
    assert prof.minutes_remaining == 0 and not prof.is_active
    assert api.get("/api/v1/billing/guest/status/?hardware_id=HW-GP2").json().get("active") in (False, None)
