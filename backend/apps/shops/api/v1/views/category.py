from drf_spectacular.utils import extend_schema
from rest_framework import generics

from apps.shops.api.v1.permissions.permissions import IsAdminOrReadOnly
from apps.shops.api.v1.serializers.category import (
    CategorySerializer,
    CategoryWithProductsSerializer,
)
from apps.shops.models import Category, Product
from apps.shops.repositories.implementation.category import CategoryRepository
from apps.shops.services.implementation.category import (
    CategoryCreateService,
    CategoryDeleteService,
    CategoryListService,
    CategoryProductsService,
    CategoryUpdateService,
)


@extend_schema(tags=["Shop - Categories"])
class CategoryListAPIView(generics.ListAPIView):
    """List all categories (Admin only)"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    service = CategoryListService(repository=CategoryRepository())

    def get_queryset(self):
        """Get queryset"""
        return self.service.execute()


@extend_schema(tags=["Shop - Categories"])
class CategoryCreateAPIView(generics.CreateAPIView):
    """Create a new category (Admin only)"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    service = CategoryCreateService(repository=CategoryRepository())

    def perform_create(self, serializer):
        """Create a new category"""
        data = serializer.validated_data
        self.service.execute(data)


@extend_schema(tags=["Shop - Categories"])
class CategoryUpdateAPIView(generics.UpdateAPIView):
    """Update a category (Admin only)"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    service = CategoryUpdateService(repository=CategoryRepository())

    lookup_field = "slug"

    def perform_update(self, serializer):
        """Update a category"""
        data = serializer.validated_data
        slug = self.kwargs.get("slug")

        self.service.execute(slug, data)


@extend_schema(tags=["Shop - Categories"])
class CategoryDestroyAPIView(generics.DestroyAPIView):
    """Delete a category (Admin only)"""

    queryset = Category.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    service = CategoryDeleteService(repository=CategoryRepository())

    lookup_field = "slug"

    def perform_destroy(self, instance):
        """Delete a category"""
        slug = self.kwargs.get("slug")
        self.service.execute(slug)


@extend_schema(tags=["Shop - Categories"])
class CategoriesProductsAPIView(generics.RetrieveAPIView):
    """List all products in a category (Admin only)"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = CategoryWithProductsSerializer
    permission_classes = [IsAdminOrReadOnly]
    service = CategoryProductsService(repository=CategoryRepository())

    lookup_field = "slug"

    def get_queryset(self):
        """Get queryset"""
        slug = self.kwargs.get("slug")
        return self.service.execute(slug)
