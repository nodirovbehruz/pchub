"""Regression: a minute-fine on a POSTPAID session must be rejected (it was a no-op
that also wrongly revoked the postpaid client's access via the realtime push)."""
import pytest


@pytest.mark.django_db
def test_fine_rejected_for_postpaid_session(api, make_club):
    from apps.computers.models import Computer
    from apps.billing.services.implementation.billing import BillingService
    club = make_club()
    pc = Computer.objects.create(name="PC-fine-pp", club=club)
    BillingService().start_guest_postpaid(computer=pc, rate_per_hour=60, admin=club.owner, club_id=club.id)

    api.force_authenticate(user=club.owner)
    resp = api.post("/api/v1/computers/admin/session/fine/",
                    {"computer_id": pc.id, "minutes": 10}, format="json")
    assert resp.status_code == 400
    assert "постоплат" in resp.json().get("error", "").lower()
