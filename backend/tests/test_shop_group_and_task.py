"""Regressions:
1. Shop "группа" (Category) create 500'd — CategoryCreateService called
   repository.create(**data) but repository.create(data: dict) takes the dict itself
   → TypeError: create() got an unexpected keyword argument 'name'. Fixed to pass data.
2. Task create round-trips: created task appears in the dashboard active list."""
import pytest


@pytest.mark.django_db
def test_shop_group_create_ok(api, make_club):
    club = make_club()
    api.force_authenticate(user=club.owner)
    r = api.post(f"/api/v1/shops/categories/create/?club={club.id}",
                 {"name": "напитки"}, format="json")
    assert r.status_code in (200, 201, 204), r.content


@pytest.mark.django_db
def test_shop_group_cyrillic_gets_valid_slug(api, make_club):
    from apps.shops.models import Category
    club = make_club()
    api.force_authenticate(user=club.owner)
    api.post(f"/api/v1/shops/categories/create/?club={club.id}",
             {"name": "Закуски"}, format="json")
    cat = Category.objects.get(name="Закуски")
    assert cat.slug and cat.slug.isascii()  # SlugField needs ASCII


@pytest.mark.django_db
def test_task_create_appears_in_dashboard(api, make_club):
    club = make_club()
    api.force_authenticate(user=club.owner)
    c = api.post("/api/v1/content/tasks/", {"club": club.id, "title": "помыть зал"},
                 format="json", HTTP_X_CLUB_ID=str(club.id))
    assert c.status_code == 201, c.content
    d = api.get(f"/api/v1/billing/dashboard/?club={club.id}")
    active = d.json().get("tasks", {}).get("active", [])
    assert any(t.get("title") == "помыть зал" for t in active), d.content
