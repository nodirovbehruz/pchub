from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.shops.api.v1.permissions.permissions import IsAdminOrReadOnly
from apps.shops.api.v1.serializers.stock import StockAdjustmentSerializer
from apps.shops.models import Stock
from apps.shops.repositories.implementation.stock import StockRepository
from apps.shops.services.implementation.stock import (
    AddToStockService,
    AdjustStockService,
    RemoveFromStockService,
)


@extend_schema(tags=["Shop - Stock"])
class StockAddAPIView(generics.CreateAPIView):
    """Add stock quantity"""

    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    service = AddToStockService(repository=StockRepository())

    def perform_create(self, serializer):
        """Add stock quantity"""
        data = serializer.validated_data

        self.service.execute(
            stock=Stock.objects.get(id=self.kwargs["pk"]),
            quantity=data.get("quantity"),
            reason=data.get("reason", "Stock added via API"),
            user=self.request.user,
        )


@extend_schema(tags=["Shop - Stock"])
class StockRemoveAPIView(generics.CreateAPIView):
    """Remove stock quantity"""

    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    service = RemoveFromStockService(repository=StockRepository())

    def perform_create(self, serializer):
        data = serializer.validated_data.copy()

        self.service.execute(
            stock=Stock.objects.get(id=self.kwargs["pk"]),
            quantity=data.get("quantity"),
            reason=data.get("reason", "Stock removed via API"),
            user=self.request.user,
        )


@extend_schema(tags=["Shop - Stock"])
class StockAdjustAPIView(generics.CreateAPIView):
    """Adjust stock quantity"""

    serializer_class = StockAdjustmentSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    service = AdjustStockService(repository=StockRepository())

    def perform_create(self, serializer):
        data = serializer.validated_data.copy()

        self.service.execute(
            stock=Stock.objects.get(id=self.kwargs["pk"]),
            quantity=data.get("quantity"),
            reason=data.get("reason", "Stock adjusted via API"),
            user=self.request.user,
        )
