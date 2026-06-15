from typing import Optional, Protocol

from django.db.models import QuerySet

from apps.shops.models import Category


class ICategoryRepository(Protocol):
    """Interface for Category repository"""

    def get_all_active(self) -> QuerySet[Category]:
        """Get all active categories"""
        pass

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID"""
        pass

    def get_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug"""
        pass

    def get_products_by_category(self, category_id: int) -> QuerySet[Category]:
        """Get all products in category"""
        pass

    def create(self, data: dict) -> Category:
        """Create new category"""
        pass

    def update(self, category: Category, data: dict) -> Category:
        """Update existing category"""
        pass

    def delete(self, category: Category) -> None:
        """Delete category"""
        pass
