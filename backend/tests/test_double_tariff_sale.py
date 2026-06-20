"""Regression: selling a tariff a SECOND time must STACK the minutes (a second hour looked
«не добавился»). Backend stacks via add_minutes (F + minutes); this asserts it and that the
guest profile ends with the sum."""
from decimal import Decimal
import pytest


@pytest.mark.django_db
def test_double_tariff_sale_stacks(api, make_club):
    from apps.computers.models import Computer
    from apps.billing.models import TariffPlan
    from apps.clubs.models import UserClubProfile
    from apps.accounts.models import CustomUser

    club = make_club()
    pc = Computer.objects.create(club=club, hardware_id="HW-D1", name="PC", is_active=True)
    tariff = TariffPlan.objects.create(name="1ch", minutes=60, price=Decimal("50000"), is_active=True)
    api.force_authenticate(user=club.owner)

    def sell():
        return api.post("/api/v1/computers/admin/session/start/",
                        {"computer_id": pc.id, "user_id": None, "tariff_id": tariff.id,
                         "payment_method": "cash", "amount_paid": 50000},
                        format="json", HTTP_X_CLUB_ID=str(club.id))

    assert sell().status_code == 200
    assert sell().status_code == 200
    guest = CustomUser.objects.get(username=f"guest-pc-{pc.id}")
    prof = UserClubProfile.objects.get(user=guest, club_id=club.id)
    assert prof.minutes_remaining == 120, prof.minutes_remaining
