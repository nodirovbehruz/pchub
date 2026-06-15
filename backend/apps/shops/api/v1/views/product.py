from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers, viewsets

from apps.clubs.api.v1.mixins import TenantFilterMixin, TenantCreateMixin, validated_club_id
from apps.shops.api.v1.permissions.permissions import IsAdminOrReadOnly
from apps.shops.api.v1.serializers.product import (
    ProductDetailSerializer,
    ProductListSerializer,
    ProductTagSerializer,
)
from apps.shops.models import Product, ProductTag, Stock
from apps.shops.repositories.implementation.product import ProductRepository
from apps.shops.services.implementation.product import (
    ProductCreateService,
    ProductDeleteService,
    ProductDetailService,
    ProductListService,
    ProductUpdateService,
)


# ── Simple admin serializer (no service layer) ────────────────────────────────
class ProductAdminSerializer(serializers.ModelSerializer):
    current_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "name", "slug", "category", "price", "purchase_price",
            "original_price", "description", "barcode", "shell_display",
            "is_active", "is_featured", "club", "current_stock", "main_image",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
            "category": {"required": True},
            "club": {"required": False, "allow_null": True},
        }

    def get_current_stock(self, obj):
        try:
            return obj.stock.quantity
        except Exception:
            return None

    def validate_slug(self, value):
        """Auto-generate slug from name if a blank slug was explicitly sent."""
        if not value:
            return self._gen_slug()
        return value

    def _gen_slug(self):
        import re, uuid
        name = (self.initial_data.get("name", "") if hasattr(self, "initial_data") else "") or ""
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return (base[:40] + "-" + uuid.uuid4().hex[:8]) if base else uuid.uuid4().hex[:16]

    def validate(self, attrs):
        # BUGFIX: the admin form doesn't send `slug`, so it was saved empty "" — the
        # SECOND product then collided on the unique slug constraint → IntegrityError
        # (HTTP 500). validate_slug only runs when slug is PRESENT in input, so generate
        # it here on CREATE when missing. (On update we keep the existing slug.)
        if self.instance is None and not attrs.get("slug"):
            attrs["slug"] = self._gen_slug()
        return attrs


# ── Admin CRUD views (id-based, used by React admin panel) ───────────────────
@extend_schema(tags=["Shop - Admin Products"])
class ProductAdminListCreateAPIView(TenantCreateMixin, generics.ListCreateAPIView):
    """GET /api/v1/shops/admin/products/?club=<id>  — list + create. Both scoped to
    the authorized club (was leaking on read and creating cross-club / NULL orphans)."""
    serializer_class = ProductAdminSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        cid = validated_club_id(self.request)
        if not cid:
            return Product.objects.none()
        return (Product.objects.filter(club_id=cid)
                .select_related("category").prefetch_related("stock").order_by("name"))


@extend_schema(tags=["Shop - Admin Products"])
class ProductAdminDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/shops/admin/products/<pk>/ — tenant-scoped (IDOR fix)."""
    serializer_class = ProductAdminSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.select_related("category").prefetch_related("stock")


@extend_schema(tags=["Shop - Admin Products"])
class ProductStockAdjustAPIView(generics.GenericAPIView):
    """POST /api/v1/shops/admin/products/<pk>/stock/
    Body: { delta: int, reason?: str }
    Adds delta to current stock (negative = remove). Creates Stock record if needed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from rest_framework.response import Response
        # SECURITY: scope to the authorized club (was Product.objects.get(pk) →
        # any operator could adjust ANY club's stock by id).
        cid = validated_club_id(request)
        if not cid:
            return Response({"error": "club required"}, status=400)
        try:
            product = Product.objects.get(pk=pk, club_id=cid)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)

        delta = int(request.data.get("delta", 0))
        if delta == 0:
            return Response({"error": "delta must be non-zero"}, status=400)

        stock, _ = Stock.objects.get_or_create(product=product, defaults={"quantity": 0})
        new_qty = max(0, stock.quantity + delta)
        stock.quantity = new_qty
        stock.save(update_fields=["quantity"])

        return Response({
            "product_id": product.pk,
            "product_name": product.name,
            "delta": delta,
            "quantity": new_qty,
        })


# ---------------------
# Product List
# ---------------------
@extend_schema(tags=["Shop - Products"])
class ProductsListAPIView(generics.ListAPIView):
    """List all products"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductListSerializer
    permission_classes = [IsAdminOrReadOnly]
    service = ProductListService(repository=ProductRepository())

    def get_queryset(self):
        return self.service.execute()


@extend_schema(tags=["Shop - Products"])
class ProductDetailAPIView(generics.RetrieveAPIView):
    """Retrieve product details"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdminOrReadOnly]
    service = ProductDetailService(repository=ProductRepository())

    lookup_field = "slug"

    def get_object(self):
        return self.service.execute(slug=self.kwargs["slug"])


@extend_schema(tags=["Shop - Products"])
class ProductCreateAPIView(generics.CreateAPIView):
    """Create a new product (Admin only)"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdminOrReadOnly]
    service = ProductCreateService(repository=ProductRepository())

    lookup_field = "slug"

    def perform_create(self, serializer):
        data = serializer.validated_data
        return self.service.execute(data)


@extend_schema(tags=["Shop - Products"])
class ProductUpdateAPIView(generics.UpdateAPIView):
    """Update a product (Admin only)"""

    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [IsAdminOrReadOnly]
    service = ProductUpdateService(repository=ProductRepository())

    lookup_field = "slug"

    def _assert_club(self, slug):
        """SECURITY: slug update/delete had no tenant scope — any admin/owner could
        edit ANY club's product by slug. Verify the product belongs to the authorized club."""
        from rest_framework.exceptions import PermissionDenied, NotFound
        u = self.request.user
        if getattr(u, "user_type", "") == "admin":
            return
        prod = Product.objects.filter(slug=slug).first()
        if not prod:
            raise NotFound("Product not found")
        cid = validated_club_id(self.request)
        if not cid or prod.club_id != cid:
            raise PermissionDenied("Нет прав на этот товар")

    def perform_update(self, serializer):
        data = serializer.validated_data
        slug = self.kwargs.get("slug")
        self._assert_club(slug)
        return self.service.execute(slug, data)


@extend_schema(tags=["Shop - Products"])
class ProductDestroyAPIView(generics.DestroyAPIView):
    """Delete a product (Admin only)"""

    queryset = Product.objects.filter(is_active=True)
    permission_classes = [IsAdminOrReadOnly]
    service = ProductDeleteService(repository=ProductRepository())

    lookup_field = "slug"

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied
        slug = self.kwargs.get("slug")
        u = self.request.user
        if getattr(u, "user_type", "") != "admin":
            cid = validated_club_id(self.request)
            if not cid or getattr(instance, "club_id", None) != cid:
                raise PermissionDenied("Нет прав на этот товар")
        return self.service.execute(slug)


# ---------------------
# Product Tags
# ---------------------
@extend_schema(tags=["Shop - Tags"])
class ProductTagViewSet(viewsets.ReadOnlyModelViewSet):
    """Product tags (read-only for users)"""

    queryset = ProductTag.objects.all()
    serializer_class = ProductTagSerializer
    lookup_field = "slug"


# @extend_schema_view(
#     list=extend_schema(description="List all product sets", tags=["Shop - Sets"]),
#     retrieve=extend_schema(description="Get set details", tags=["Shop - Sets"]),
#     create=extend_schema(description="Create set (Admin only)", tags=["Shop - Sets"]),
#     update=extend_schema(description="Update set (Admin only)", tags=["Shop - Sets"]),
#     destroy=extend_schema(description="Delete set (Admin only)", tags=["Shop - Sets"]),
# )
# class ProductSetViewSet(viewsets.ModelViewSet):
#     """Product sets/bundles CRUD endpoints"""
#
#     queryset = ProductSet.objects.filter(is_active=True).prefetch_related('items__product')
#     permission_classes = [IsAdminOrReadOnly]
#     filter_backends = [filters.SearchFilter, filters.OrderingFilter]
#     search_fields = ['name', 'name_ru', 'name_uz', 'description']
#     ordering_fields = ['name', 'price', 'created_at', 'order']
#     ordering = ['order', 'name']
#     lookup_field = 'slug'
#
#     def get_serializer_class(self):
#         if self.action == 'retrieve':
#             return ProductSetDetailSerializer
#         return ProductSetListSerializer
#
#     @extend_schema(description="Get featured sets", tags=["Shop - Sets"])
#     @action(detail=False, methods=['get'])
#     def featured(self, request):
#         """Get featured product sets"""
#         sets = self.get_queryset().filter(is_featured=True)
#         serializer = self.get_serializer(sets, many=True)
#         return Response(serializer.data)
