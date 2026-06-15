from typing import Any, Dict, Optional, Protocol

from django.db.models import QuerySet

from apps.shops.models import Category


class ICategoryCreateService(Protocol):
    """Interface for Category create service"""

    def execute(self, data: Dict[str, Any]) -> Category:
        """Create new category"""
        pass


class ICategoryUpdateService(Protocol):
    """Interface for Category update service"""

    def execute(self, slug: str, data: Dict[str, Any]) -> Category:
        """Update category"""
        pass


class ICategoryDeleteService(Protocol):
    """Interface for Category delete service"""

    def execute(self, slug: str) -> None:
        """Delete category"""
        pass


class ICategoryListService(Protocol):
    """Interface for Category list service"""

    def execute(self, is_active: bool = True) -> QuerySet[Category]:
        """List all categories"""
        pass


class ICategoryProductsService(Protocol):
    """Interface for Category products service"""

    def execute(self, slug: str) -> QuerySet:
        """Get all products in category"""
        pass
