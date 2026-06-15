from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from apps.shops.models import Product
from apps.shops.repositories.implementation.product import ProductRepository
from apps.shops.repositories.interface.product import IProductRepository
from apps.shops.services.interface.product import (
    IProductCreateService,
    IProductDeleteService,
    IProductGetService,
    IProductListService,
    IProductUpdateService,
)


class ProductListService(IProductListService):
    """Product list service implementation"""

    def __init__(self, repository: IProductRepository = ProductRepository()):
        self.repository = repository

    def execute(self, is_active: bool = True) -> QuerySet[Product]:
        """List all products"""
        return self.repository.get_all(is_active=is_active)


class ProductDetailService(IProductGetService):
    """Product get service implementation"""

    def __init__(self, repository: IProductRepository = ProductRepository()):
        self.repository = repository

    def execute(self, slug: str) -> Optional[Product]:
        """Get product by slug"""
        return self.repository.get_by_slug(slug=slug)


class ProductCreateService(IProductCreateService):
    """Product create service implementation"""

    def __init__(self, repository: IProductRepository = ProductRepository()):
        self.repository = repository

    def execute(self, data: Dict[str, Any]) -> Product:
        """Create new product"""
        return self.repository.create(**data)


class ProductUpdateService(IProductUpdateService):
    """Product update service implementation"""

    def __init__(self, repository: IProductRepository = ProductRepository()):
        self.repository = repository

    def execute(self, slug: str, data: Dict[str, Any]) -> Product:
        """Update product"""
        product = self.repository.get_by_slug(slug=slug)

        if not product:
            raise ValidationError("Product not found")

        return self.repository.update(product, **data)


class ProductDeleteService(IProductDeleteService):
    """Product delete service implementation"""

    def __init__(self, repository: IProductRepository = ProductRepository()):
        self.repository = repository

    def execute(self, slug: str) -> None:
        """Delete product"""
        product = self.repository.get_by_slug(slug=slug)

        self.repository.delete(product=product)
