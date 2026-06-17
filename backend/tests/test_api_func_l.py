"""Regression: deleting a non-empty product category must be REFUSED — it used to
CASCADE-delete every product in it (and their stock/cart/order items)."""
from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_category_delete_blocked_when_not_empty():
    from apps.shops.models import Category, Product
    from apps.shops.services.implementation.category import CategoryDeleteService
    from rest_framework.exceptions import ValidationError

    cat = Category.objects.create(name="Drinks", slug="drinks-x")
    Product.objects.create(name="Cola", slug="cola-x", category=cat, price=Decimal("10"))

    with pytest.raises(ValidationError):
        CategoryDeleteService().execute("drinks-x")

    assert Category.objects.filter(slug="drinks-x").exists()  # category not deleted
    assert Product.objects.filter(slug="cola-x").exists()     # product NOT cascade-deleted


@pytest.mark.django_db
def test_empty_category_can_still_be_deleted():
    from apps.shops.models import Category
    from apps.shops.services.implementation.category import CategoryDeleteService
    Category.objects.create(name="Empty", slug="empty-x")
    CategoryDeleteService().execute("empty-x")
    assert not Category.objects.filter(slug="empty-x").exists()
