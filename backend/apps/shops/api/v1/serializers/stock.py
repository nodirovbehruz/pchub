from rest_framework import serializers

from apps.shops.models import Stock, StockTransaction


class StockInfoSerializer(serializers.ModelSerializer):
    """Stock information for product"""

    class Meta:
        model = Stock
        fields = [
            "quantity",
            "available_quantity",
            "is_low_stock",
            "is_out_of_stock",
            "low_stock_threshold",
        ]
        read_only_fields = ["available_quantity", "is_low_stock", "is_out_of_stock"]


class StockSerializer(serializers.ModelSerializer):
    """Stock management serializer"""

    product_name = serializers.CharField(source="product.name", read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Stock
        fields = [
            "id",
            "product",
            "product_name",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "low_stock_threshold",
            "is_low_stock",
            "is_out_of_stock",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class StockAdjustmentSerializer(serializers.Serializer):
    """Serializer for stock adjustments"""

    quantity = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(required=False, allow_blank=True)


class StockTransactionSerializer(serializers.ModelSerializer):
    """Stock transaction history serializer"""

    product_name = serializers.CharField(source="stock.product.name", read_only=True)
    user_username = serializers.CharField(
        source="user.username", read_only=True, allow_null=True
    )

    class Meta:
        model = StockTransaction
        fields = [
            "id",
            "stock",
            "product_name",
            "transaction_type",
            "quantity",
            "quantity_before",
            "quantity_after",
            "reason",
            "reference_id",
            "user",
            "user_username",
            "created_at",
        ]
        read_only_fields = ["created_at"]
