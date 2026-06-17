"""Functional-audit batch C regressions."""
import re

import pytest


# ── Cyrillic game name must still get a valid (ASCII) slug → routes resolve ──
@pytest.mark.django_db
def test_game_create_cyrillic_name_gets_valid_slug():
    from apps.games.services.implementation.game import GameCreateService
    g = GameCreateService().execute({"name": "Контра Страйк"})
    assert g.slug, "slug must not be empty"
    assert re.fullmatch(r"[a-z0-9-]+", g.slug), f"slug must be ASCII slug, got {g.slug!r}"


# ── Admin can see (and thus re-enable) INACTIVE games via ?all=1 ─────────────
@pytest.mark.django_db
def test_games_admin_list_includes_inactive_with_all(api, make_user):
    from apps.games.models import Game
    g = Game.objects.create(name="Hidden Game", slug="hidden-game", is_active=False)
    api.force_authenticate(user=make_user())

    def _ids(resp):
        data = resp.json()
        rows = data.get("results", data) if isinstance(data, dict) else data
        return [r["id"] for r in rows]

    with_all = api.get("/api/v1/games/games/?all=1&limit=500")
    assert with_all.status_code == 200
    assert g.id in _ids(with_all)        # admin sees the disabled game

    default = api.get("/api/v1/games/games/?limit=500")
    assert g.id not in _ids(default)     # shell (default) does not
