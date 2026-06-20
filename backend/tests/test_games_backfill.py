"""Regression: a PC that registered AFTER games were added (or after a DB reset) has no
ComputerGame links → the shell showed «Игр пока нет». get_computer_games now backfills any
active games the computer is missing, so the catalog appears."""
import pytest


@pytest.mark.django_db
def test_get_computer_games_backfills_for_new_pc(make_club):
    from apps.computers.models import Computer, ComputerGame
    from apps.games.models import Game
    from apps.games.services.implementation.session import GameSessionService

    club = make_club()
    # Game created BEFORE this PC exists → its post_save signal links to 0 computers.
    Game.objects.create(name="CS2", slug="cs2-bk", platform="steam", is_active=True)
    pc = Computer.objects.create(club=club, hardware_id="HW-BK1", name="PC", is_active=True)
    assert not ComputerGame.objects.filter(computer=pc).exists()  # not linked yet

    data = GameSessionService().get_computer_games(hardware_id="HW-BK1")
    names = [g["game"].name for g in data["games"]]
    assert "CS2" in names, names  # backfilled → appears in the shell
