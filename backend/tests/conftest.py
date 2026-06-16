"""Shared fixtures/factories for the regression suite.

force_authenticate is used so tests exercise view-level authorization and tenant
scoping (permissions, validated_club_id, IDOR guards) without JWT plumbing. Requests
still pass through the real middleware stack (incl. ClubTenantMiddleware), so ?club=
behaves as in production.
"""
import itertools
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

_counter = itertools.count(1)


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make(username=None, user_type="user", **kw):
        n = next(_counter)
        username = username or f"user{n}"
        User = get_user_model()
        u = User.objects.create_user(
            username=username, email=f"{username}@test.local", password="pw12345", **kw
        )
        if user_type and getattr(u, "user_type", None) != user_type:
            u.user_type = user_type
            u.save(update_fields=["user_type"])
        return u
    return _make


@pytest.fixture
def make_club(db, make_user):
    def _make(owner=None, name=None):
        from apps.clubs.models import Club
        n = next(_counter)
        owner = owner or make_user(username=f"owner{n}", user_type="user")
        return Club.objects.create(owner=owner, name=name or f"Club {n}")
    return _make


@pytest.fixture
def make_membership(db):
    def _make(user, club, role="operator", is_active=True):
        from apps.clubs.models import ClubMembership
        return ClubMembership.objects.create(user=user, club=club, role=role, is_active=is_active)
    return _make


@pytest.fixture
def make_profile(db):
    def _make(user, club, **kw):
        from apps.clubs.models import UserClubProfile
        defaults = dict(deposit_money=Decimal("0"), bonus_balance=Decimal("0"),
                        minutes_remaining=0)
        defaults.update(kw)
        return UserClubProfile.objects.create(user=user, club=club, **defaults)
    return _make


@pytest.fixture
def make_category(db):
    def _make(name=None):
        from apps.shops.models import Category
        n = next(_counter)
        return Category.objects.create(name=name or f"Cat {n}", slug=f"cat-{n}")
    return _make


@pytest.fixture
def make_product(db, make_category):
    def _make(club, category=None, price="100.00", **kw):
        from apps.shops.models import Product
        n = next(_counter)
        category = category or make_category()
        return Product.objects.create(
            name=kw.pop("name", f"Product {n}"), slug=f"product-{n}",
            category=category, club=club, price=Decimal(str(price)), **kw,
        )
    return _make
