"""Functional-audit batch E regressions (500 guards + dedup)."""
import pytest


# ── ?year=abc on my-visits must be 400, not 500 ──────────────────────────────
@pytest.mark.django_db
def test_my_visits_bad_year_is_400(api, make_user):
    api.force_authenticate(user=make_user())
    resp = api.get("/api/v1/billing/my-visits/", {"year": "abc"})
    assert resp.status_code == 400  # was 500 (int('abc'))


# ── Long client-group names that collide after 16-char truncate → 400, not 500 ─
@pytest.mark.django_db
def test_client_group_long_name_collision_no_500(api, make_club):
    club = make_club()
    api.force_authenticate(user=club.owner)
    a = "A" * 20  # truncates to 16 A's
    b = "A" * 18 + "BB"  # also truncates to 16 A's
    r1 = api.post(f"/api/v1/clubs/client-groups/?club={club.id}", {"name": a}, format="json")
    assert r1.status_code == 201, r1.content
    r2 = api.post(f"/api/v1/clubs/client-groups/?club={club.id}", {"name": b}, format="json")
    assert r2.status_code == 400  # caught as duplicate, NOT a 500 IntegrityError
