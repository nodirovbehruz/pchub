"""Functional-audit batch A regressions (500 hardening + state validation)."""
import pytest


# ── Booking list: malformed ?from/?to must not 500 ───────────────────────────
@pytest.mark.django_db
def test_booking_list_garbage_date_no_500(api, make_club):
    club = make_club()
    api.force_authenticate(user=club.owner)
    resp = api.get("/api/v1/bookings/", {"club": club.id, "from": "abc", "to": ")("})
    assert resp.status_code == 200  # was 500 (ValidationError on raw filter)


# ── Booking create with empty hosts must be rejected (phantom booking) ───────
@pytest.mark.django_db
def test_booking_create_empty_hosts_rejected(api, make_club):
    from django.utils import timezone
    from datetime import timedelta
    club = make_club()
    api.force_authenticate(user=club.owner)
    base = timezone.now().replace(microsecond=0)
    resp = api.post(
        f"/api/v1/bookings/?club={club.id}",
        {"from_at": (base + timedelta(hours=1)).isoformat(),
         "to_at": (base + timedelta(hours=2)).isoformat(), "hosts": []},
        format="json",
    )
    assert resp.status_code == 400


# ── Review create with no resolvable club → 400, not 500 ─────────────────────
@pytest.mark.django_db
def test_review_create_without_club_is_400(api, make_user):
    api.force_authenticate(user=make_user())
    resp = api.post("/api/v1/sessions/reviews/", {"rating": 5, "comment": "ok"}, format="json")
    assert resp.status_code == 400  # was 500 (NOT NULL club IntegrityError)
