"""Regression: starting a guest postpaid session over an already-running one must NOT
wipe accrued unbilled minutes (lost revenue) — it must reject."""
import pytest


@pytest.mark.django_db
def test_start_guest_postpaid_rejects_double_start(make_club):
    from apps.computers.models import Computer
    from apps.clubs.models import UserClubProfile
    from apps.billing.services.implementation.billing import BillingService
    from rest_framework.exceptions import ValidationError

    club = make_club()
    pc = Computer.objects.create(name="PC-guest-1", club=club)
    svc = BillingService()

    svc.start_guest_postpaid(computer=pc, rate_per_hour=60, admin=club.owner, club_id=club.id)

    guest = svc._get_or_create_guest_user(pc)
    prof = UserClubProfile.objects.get(user=guest, club_id=club.id)
    prof.postpaid_minutes = 30  # simulate accrued unbilled time
    prof.save(update_fields=["postpaid_minutes"])

    with pytest.raises(ValidationError):
        svc.start_guest_postpaid(computer=pc, rate_per_hour=60, admin=club.owner, club_id=club.id)

    prof.refresh_from_db()
    assert prof.postpaid_minutes == 30  # NOT reset to 0
