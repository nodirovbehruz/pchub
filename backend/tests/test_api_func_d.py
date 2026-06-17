"""Functional-audit batch D regressions (ignored list filters + 500 guard)."""
import pytest


@pytest.mark.django_db
def test_task_list_is_finished_filter(api, make_club):
    from apps.content.models import Task
    club = make_club()
    Task.objects.create(club=club, title="done", is_finished=True)
    Task.objects.create(club=club, title="todo", is_finished=False)
    api.force_authenticate(user=club.owner)

    resp = api.get("/api/v1/content/tasks/", {"club": club.id, "is_finished": "1"})
    assert resp.status_code == 200
    data = resp.json()
    rows = data.get("results", data) if isinstance(data, dict) else data
    titles = [r["title"] for r in rows]
    assert "done" in titles and "todo" not in titles


@pytest.mark.django_db
def test_admincall_is_answered_filter(api, make_club, make_user):
    from django.utils import timezone
    from apps.sessions_.models import AdminCall
    club = make_club()
    AdminCall.objects.create(club=club, client=make_user(), answered_at=timezone.now())
    AdminCall.objects.create(club=club, client=make_user(), answered_at=None)
    api.force_authenticate(user=club.owner)

    resp = api.get("/api/v1/sessions/admin-calls/", {"club": club.id, "is_answered": "0"})
    assert resp.status_code == 200
    data = resp.json()
    rows = data.get("results", data) if isinstance(data, dict) else data
    assert len(rows) == 1 and rows[0]["answered_at"] is None


@pytest.mark.django_db
def test_game_category_create_bad_order_is_400(api, make_user):
    api.force_authenticate(user=make_user())
    resp = api.post("/api/v1/games/categories/", {"name": "Шутеры", "order": "abc"}, format="json")
    assert resp.status_code == 400  # was 500 (order='abc' into PositiveIntegerField)
