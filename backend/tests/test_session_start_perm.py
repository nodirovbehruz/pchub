"""Regression: starting a session (selling a tariff to a walk-in guest) is front-desk
work — the PC's club staff (owner/manager/operator) must be able to do it, not only the
platform admin (was [IsAuthenticated, IsAdmin] → owner got HTTP 403). A non-staff user
still can't (per-club IDOR guard)."""
import pytest


@pytest.mark.django_db
def test_owner_can_start_guest_session(api, make_club):
    from apps.computers.models import Computer
    club = make_club()
    pc = Computer.objects.create(club=club, hardware_id="HW-S1", name="PC-1", is_active=True)
    api.force_authenticate(user=club.owner)
    r = api.post("/api/v1/computers/admin/session/start/",
                 {"computer_id": pc.id, "user_id": None, "tariff_id": None,
                  "payment_method": "cash", "amount_paid": 30000},
                 format="json", HTTP_X_CLUB_ID=str(club.id))
    assert r.status_code in (200, 201), r.content


@pytest.mark.django_db
def test_outsider_cannot_start_session(api, make_club, make_user):
    from apps.computers.models import Computer
    club = make_club()
    pc = Computer.objects.create(club=club, hardware_id="HW-S2", name="PC-2", is_active=True)
    api.force_authenticate(user=make_user())  # not staff of this club
    r = api.post("/api/v1/computers/admin/session/start/",
                 {"computer_id": pc.id, "payment_method": "cash", "amount_paid": 0},
                 format="json", HTTP_X_CLUB_ID=str(club.id))
    assert r.status_code == 403, r.content
