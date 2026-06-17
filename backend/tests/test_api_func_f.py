"""Functional-audit batch F regressions (validation + state stamping)."""
from decimal import Decimal

import pytest


# ── News title must be >= 2 chars ────────────────────────────────────────────
@pytest.mark.django_db
def test_news_title_min_length():
    from apps.content.api.v1.urls import NewsSerializer
    bad = NewsSerializer(data={"title": "X"})
    assert not bad.is_valid()
    assert "title" in bad.errors
    ok = NewsSerializer(data={"title": "Новость дня"})
    ok.is_valid()
    assert "title" not in ok.errors


# ── Finishing a client session stamps finished_at ────────────────────────────
@pytest.mark.django_db
def test_client_session_finish_stamps_timestamp(api, make_club, make_user):
    from apps.sessions_.models import ClientSession
    club = make_club()
    cs = ClientSession.objects.create(
        club=club, client=make_user(), status="active", total_cost=Decimal("0"))
    assert cs.finished_at is None

    api.force_authenticate(user=club.owner)
    resp = api.patch(f"/api/v1/sessions/{cs.id}/?club={club.id}",
                     {"status": "finished"}, format="json")
    assert resp.status_code in (200, 202), resp.content
    cs.refresh_from_db()
    assert cs.status == "finished"
    assert cs.finished_at is not None
