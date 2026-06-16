"""Smoke test — proves the pytest harness builds the sqlite schema and ORM works."""
import pytest
from django.contrib.auth import get_user_model


@pytest.mark.django_db
def test_user_create():
    User = get_user_model()
    u = User.objects.create_user(username="smoke", email="smoke@test.local", password="x")
    assert u.pk is not None
    assert User.objects.filter(username="smoke").exists()
