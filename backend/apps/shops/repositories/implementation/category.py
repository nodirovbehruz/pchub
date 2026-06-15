from typing import Optional

from django.db.models import Q, QuerySet

from apps.shops.models import Category
from apps.shops.repositories.interface.category import ICategoryRepository


class CategoryRepository(ICategoryRepository):
    """Category repository implementation"""

    def __init__(self):
        self.model = Category

    def get_all_active(self, is_active: Optional[bool] = None) -> QuerySet[Category]:
        """Get all categories"""
        queryset = Category.objects.all()
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset.order_by("order", "name")

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID"""
        try:
            return Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug"""
        try:
            return Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            return None

    def get_products_by_category(self, category_id: int) -> QuerySet[Category]:
        """Get all products in category"""
        return self.model.objects.filter(
            is_active=True, id=category_id
        ).prefetch_related("products")

    def create(self, data: dict) -> Category:
        """Create new category"""
        return Category.objects.create(**data)

    def update(self, category: Category, data: dict) -> Category:
        """Update category"""
        for key, value in data.items():
            setattr(category, key, value)
        category.save()
        return category

    def delete(self, category: Category) -> None:
        """Delete category (soft delete)"""
        category.is_active = False
        category.save()
