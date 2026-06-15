from typing import Any, Dict

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from apps.shops.models import Category
from apps.shops.repositories.implementation.category import CategoryRepository
from apps.shops.repositories.interface.category import ICategoryRepository
from apps.shops.services.interface.category import (
    ICategoryCreateService,
    ICategoryDeleteService,
    ICategoryListService,
    ICategoryProductsService,
    ICategoryUpdateService,
)


class CategoryCreateService(ICategoryCreateService):
    """Category create service"""

    def __init__(self, repository: ICategoryRepository = CategoryRepository()):
        self.repository = repository

    def execute(self, data: Dict[str, Any]) -> Category:
        """Create new category"""

        if self.repository.get_by_slug(data.get("slug")):
            raise ValidationError(
                f"Category with slug '{data.get('slug')}' already exists"
            )

        return self.repository.create(**data)


class CategoryUpdateService(ICategoryUpdateService):
    """Category update service"""

    def __init__(self, repository: ICategoryRepository = CategoryRepository()):
        self.repository = repository

    def execute(self, slug: str, data: Dict[str, Any]) -> Category:
        """Update category"""

        category = self.repository.get_by_slug(slug)
        if not category:
            raise ValidationError(f"Category with slug '{slug}' not found")

        for key, value in data.items():
            setattr(category, key, value)
        category.save()
        return category


class CategoryDeleteService(ICategoryDeleteService):
    """Category delete service"""

    def __init__(self, repository: ICategoryRepository = CategoryRepository()):
        self.repository = repository

    def execute(self, slug: str) -> None:
        """Delete category"""

        category = self.repository.get_by_slug(slug)
        if not category:
            raise ValidationError(f"Category with slug '{slug}' not found")

        category.delete()


class CategoryListService(ICategoryListService):
    """Category list service"""

    def __init__(self, repository: ICategoryRepository = CategoryRepository()):
        self.repository = repository

    def execute(self, is_active: bool = True) -> QuerySet[Category]:
        """List all categories"""
        return self.repository.get_all_active()


class CategoryProductsService(ICategoryProductsService):
    """Category products service"""

    def __init__(self, repository: ICategoryRepository = CategoryRepository()):
        self.repository = repository

    def execute(self, slug: str) -> QuerySet:
        """Get all products in category"""

        category = self.repository.get_by_slug(slug)
        if not category:
            raise ValidationError(f"Category with slug '{slug}' not found")
        return self.repository.get_products_by_category(category.id)
