"""The shell games card binds the `icon` JSON field. The admin only uploads ONE image —
the cover (header_image) — so `icon` must fall back to the uploaded cover, otherwise the
card showed a random picsum placeholder («не та иконка») instead of the operator's cover."""
import io
import pytest


def _png():
    from PIL import Image
    f = io.BytesIO()
    Image.new("RGB", (32, 32), (0, 120, 255)).save(f, "PNG")
    f.seek(0)
    f.name = "chrome.png"
    return f


@pytest.mark.django_db
def test_game_icon_falls_back_to_uploaded_cover(api, make_club):
    from apps.games.models import Game
    from apps.games.api.v1.serializers.game import GameListSerializer
    club = make_club()
    api.force_authenticate(user=club.owner)
    r = api.post(
        f"/api/v1/games/admin/games/create/?club={club.id}",
        {"name": "chrome", "platform": "local",
         "executable_path": "C:/chrome.exe", "header_image": _png()},
        format="multipart")
    assert r.status_code == 201, r.content
    g = Game.objects.get(name="chrome")
    assert g.header_image, "uploaded cover was not saved"
    icon = GameListSerializer(g).data["icon"]
    assert "picsum" not in icon, f"icon fell back to placeholder: {icon}"
    assert "games/headers" in icon, f"icon should be the uploaded cover: {icon}"


@pytest.mark.django_db
def test_game_serializer_includes_category_name():
    """The shell's computer-games endpoint uses GameSerializer; it must expose category_name
    so the shell groups games into sections (Шутеры/Games/…) instead of all under «Прочее»."""
    from apps.games.models import Game
    from apps.games.models.game import Category
    from apps.games.api.v1.serializers.game import GameSerializer
    cat = Category.objects.create(name="Шутеры", slug="shooters-x")
    g = Game.objects.create(name="CS2", slug="cs2-x", platform="steam", category=cat)
    assert GameSerializer(g).data["category_name"] == "Шутеры"
