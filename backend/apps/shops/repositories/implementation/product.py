from typing import Optional

from django.db.models import QuerySet

from apps.shops.models import Product
from apps.shops.repositories.interface.product import IProductRepository


class ProductRepository(IProductRepository):
    """Product repository implementation"""

    def get_all(self, is_active: Optional[bool] = None) -> QuerySet[Product]:
        """Get all products"""
        return Product.objects.all()

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return Product.objects.filter(id=product_id).first()

    def get_by_slug(self, slug: str) -> Optional[Product]:
        """Get product by slug"""
        return Product.objects.filter(slug=slug).first()

    def create(self, data: dict) -> Product:
        """Create new product"""
        return Product.objects.create(**data)

    def update(self, product: Product, data: dict) -> Product:
        """Update product"""
        for key, value in data.items():
            setattr(product, key, value)
        product.save()
        return product

    def delete(self, product: Product) -> None:
        """Delete product"""
        product.delete()
