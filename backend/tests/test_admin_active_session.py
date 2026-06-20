"""Regression: a tariff bought ON THE SHELL (guest prepaid OR a registered client) creates
no ClientSession, so the admin PC list showed the PC as free. active_sessions_map now
surfaces prepaid guests AND seated, LOGGED-IN registered clients. A logged-out client
(is_active_session=False, but active_hardware_id not cleared) must NOT show."""
import pytest


def _pc_in_list(api, club, pc_id):
    r = api.get(f"/api/v1/computers/?club={club.id}")
    assert r.status_code == 200, r.content
    body = r.json()
    pcs = body.get("results") if isinstance(body, dict) else body
    return next(p for p in pcs if p["id"] == pc_id)


@pytest.mark.django_db
def test_guest_prepaid_shows_in_admin(api, make_club):
    from apps.computers.models import Computer
    from apps.accounts.models import CustomUser
    from apps.clubs.models import UserClubProfile
    club = make_club()
    pc = Computer.objects.create(club=club, hardware_id="HW-AS1", name="PC", is_active=True)
    guest = CustomUser.objects.create(username=f"guest-pc-{pc.id}", user_type="user")
    UserClubProfile.objects.create(user=guest, club=club, is_guest=True,
                                   session_mode="prepaid", is_active=True, minutes_remaining=60)
    api.force_authenticate(user=club.owner)
    p = _pc_in_list(api, club, pc.id)
    assert p["active_session"] is not None and p["active_session"]["client"] == "Гость", p


@pytest.mark.django_db
def test_logged_in_client_shows_logged_out_does_not(api, make_club, make_user):
    from apps.computers.models import Computer
    from apps.clubs.models import UserClubProfile
    club = make_club()
    pc = Computer.objects.create(club=club, hardware_id="HW-AS2", name="PC", is_active=True)
    client = make_user(username="player1")
    client.active_hardware_id = "HW-AS2"
    client.is_active_session = True
    client.save(update_fields=["active_hardware_id", "is_active_session"])
    UserClubProfile.objects.create(user=client, club=club, is_active=True,
                                   session_mode="prepaid", minutes_remaining=30)
    api.force_authenticate(user=club.owner)

    p = _pc_in_list(api, club, pc.id)
    assert p["active_session"] is not None and p["active_session"]["client"] == "player1", p

    # Client logs out: is_active_session=False (active_hardware_id stays set) → must NOT show.
    client.is_active_session = False
    client.save(update_fields=["is_active_session"])
    p = _pc_in_list(api, club, pc.id)
    assert p["active_session"] is None, p
