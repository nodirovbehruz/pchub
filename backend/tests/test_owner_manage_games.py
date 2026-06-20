"""Regression: a club owner can manage the game catalog (create), not only the platform
admin. Games create/update/delete switched from IsPlatformAdminOrReadOnly to the
owner-friendly IsAdminOrReadOnly, since for a single-club deployment the owner runs the
catalog. (Clients — non-members — still can't write.)"""
import pytest


@pytest.mark.django_db
def test_owner_can_create_game(api, make_club, make_user):
    from apps.games.models import Game
    club = make_club()
    api.force_authenticate(user=club.owner)
    resp = api.post(
        f"/api/v1/games/admin/games/create/?club={club.id}",
        {"name": "Chrome", "platform": "local", "executable_path": "C:\\\\chrome.exe"},
        format="json")
    assert resp.status_code in (200, 201), resp.content
    assert Game.objects.filter(name="Chrome").exists()


@pytest.mark.django_db
def test_plain_client_cannot_create_game(api, make_club, make_user):
    club = make_club()
    client = make_user()  # not owner, not a club member
    api.force_authenticate(user=client)
    resp = api.post(
        f"/api/v1/games/admin/games/create/?club={club.id}",
        {"name": "Hacky", "platform": "local", "executable_path": "C:\\\\x.exe"},
        format="json")
    assert resp.status_code == 403, resp.content
