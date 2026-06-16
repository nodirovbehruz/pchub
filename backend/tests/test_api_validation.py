"""Input-validation regression tests — these inputs previously caused HTTP 500."""
from datetime import timedelta

import pytest
from django.utils import timezone


# ── ?computer_id=abc must be 400, not 500 ────────────────────────────────────
@pytest.mark.django_db
def test_computer_games_non_numeric_id_returns_400(api, make_user):
    api.force_authenticate(user=make_user())
    resp = api.get("/api/v1/games/computer/games/", {"computer_id": "abc"})
    assert resp.status_code == 400  # was 500 (int('abc') ValueError)


# ── Duplicate app_id on game UPDATE must be rejected (was 500 on session ping) ─
@pytest.mark.django_db
def test_game_update_duplicate_app_id_rejected():
    from apps.games.models import Game
    from apps.games.api.v1.serializers.game import GameUpdateSerializer
    Game.objects.create(name="Alpha", slug="alpha", app_id="100")
    g2 = Game.objects.create(name="Beta", slug="beta", app_id="200")

    s = GameUpdateSerializer(instance=g2, data={"app_id": "100"}, partial=True)
    assert not s.is_valid()
    assert "app_id" in s.errors

    # A non-colliding change is still allowed.
    ok = GameUpdateSerializer(instance=g2, data={"app_id": "300"}, partial=True)
    assert ok.is_valid(), ok.errors


# ── Review rating must be within 1..5 ────────────────────────────────────────
@pytest.mark.django_db
def test_review_rating_out_of_range_rejected():
    from apps.sessions_.api.v1.serializers import ReviewSerializer
    bad = ReviewSerializer(data={"rating": 9})
    assert not bad.is_valid()
    assert "rating" in bad.errors
    good = ReviewSerializer(data={"rating": 5})
    assert good.is_valid(), good.errors


# ── News show_until < show_from must be rejected (silent permanent invisibility)
def test_news_reversed_window_rejected():
    from rest_framework.exceptions import ValidationError
    from apps.content.api.v1.urls import NewsSerializer
    now = timezone.now()
    s = NewsSerializer()
    with pytest.raises(ValidationError):
        s.validate({"show_from": now, "show_until": now - timedelta(days=1)})
    # A correctly-ordered window passes.
    assert s.validate({"show_from": now, "show_until": now + timedelta(days=1)})
