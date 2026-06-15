from typing import Optional, Protocol

from django.db.models import QuerySet

from apps.shops.models import Product


class IProductRepository(Protocol):
    """Interface for Product repository"""

    def get_all(self, is_active: Optional[bool] = None) -> QuerySet[Product]:
        """Get all products"""
        pass

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        pass

    def get_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug"""
        pass

    def create(self, data: dict) -> Product:
        """Create new product"""
        pass

    def update(self, product: Product, data: dict) -> Product:
        """Update product"""
        pass

    def delete(self, product: Product) -> None:
        """Delete product"""
        pass
