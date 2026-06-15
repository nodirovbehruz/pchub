from typing import Any, Dict, Optional, Protocol

from django.db.models import QuerySet

from apps.shops.models import Product


class IProductListService(Protocol):
    """Interface for Product list service"""

    def execute(self, is_active: bool = True) -> QuerySet[Product]:
        """List all products"""
        pass


class IProductGetService(Protocol):
    """Interface for Product get service"""

    def execute(self, slug: str) -> Optional[Product]:
        """Get product by slug"""
        pass


class IProductCreateService(Protocol):
    """Interface for Product create service"""

    def execute(self, data: Dict[str, Any]) -> Product:
        """Create new product"""
        pass


class IProductUpdateService(Protocol):
    """Interface for Product update service"""

    def execute(self, slug: str, data: Dict[str, Any]) -> Product:
        """Update product"""
        pass


class IProductDeleteService(Protocol):
    """Interface for Product delete service"""

    def execute(self, slug: str) -> None:
        """Delete product"""
        pass
