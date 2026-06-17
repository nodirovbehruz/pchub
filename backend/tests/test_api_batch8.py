"""Batch 8 — login lookup, task completion stamping."""
import pytest


# ── Username login must be case-insensitive (matches case-insensitive registration) ─
@pytest.mark.django_db
def test_login_lookup_is_case_insensitive(make_user):
    from apps.accounts.repositories.implementation.account import AccountRepository
    u = make_user(username="JohnDoe")
    repo = AccountRepository()
    found = repo.get_user_by_username("johndoe")
    assert found is not None
    assert found.id == u.id


# ── Completing a task stamps finished_at / finished_by ───────────────────────
@pytest.mark.django_db
def test_task_finished_at_stamped_on_completion(api, make_club):
    from apps.content.models import Task
    club = make_club()
    t = Task.objects.create(club=club, title="Do it")
    assert t.finished_at is None

    api.force_authenticate(user=club.owner)
    resp = api.patch(f"/api/v1/content/tasks/{t.id}/?club={club.id}",
                     {"is_finished": True}, format="json")
    assert resp.status_code == 200, resp.content

    t.refresh_from_db()
    assert t.is_finished
    assert t.finished_at is not None
    assert t.finished_by_id == club.owner.id
