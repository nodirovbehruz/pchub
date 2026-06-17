"""Regression: the Clients table must show PER-CLUB remaining time, not the legacy
global UserBalance."""
import pytest


@pytest.mark.django_db
def test_client_list_shows_per_club_minutes(api, make_club, make_user, make_profile):
    from apps.billing.models import UserBalance
    club = make_club()
    client = make_user()
    make_profile(client, club, minutes_remaining=30)        # per-club time
    bal, _ = UserBalance.objects.get_or_create(user=client)  # global time (different)
    bal.minutes_remaining = 100
    bal.save(update_fields=["minutes_remaining"])

    api.force_authenticate(user=club.owner)
    resp = api.get(f"/api/v1/billing/admin/users/?club={club.id}")
    assert resp.status_code == 200
    data = resp.json()
    rows = data.get("results", data) if isinstance(data, dict) else data
    row = next((r for r in rows if r["id"] == str(client.id)), None)
    assert row is not None, "client must appear in the club list"
    assert row["minutes_remaining"] == 30  # per-club, NOT the global 100
