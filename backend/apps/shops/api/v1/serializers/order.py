from rest_framework import serializers

from apps.shops.models import Order, OrderItem, Product


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for order items"""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_image = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_image",
            "quantity",
            "price",
            "subtotal",
        ]

    def get_product_image(self, obj):
        if obj.product and obj.product.main_image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.product.main_image.url)
        return None


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders"""

    items = OrderItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    items_summary = serializers.SerializerMethodField()
    computer_name = serializers.CharField(source="computer.name", read_only=True, default=None)
    computer_id = serializers.IntegerField(source="computer.id", read_only=True, default=None)
    client = serializers.CharField(source="account.username", read_only=True, default=None)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total_price",
            "created_at",
            "updated_at",
            "items",
            "item_count",
            "items_summary",
            "computer_name",
            "computer_id",
            "client",
        ]

    def get_item_count(self, obj):
        return obj.items.count()

    def get_items_summary(self, obj):
        """Return a summary string of items like 'Lays - 2шт, Coca Cola - 1шт'"""
        items = obj.items.all()[:3]  # Show first 3 items
        summary_parts = []
        for item in items:
            summary_parts.append(f"{item.product.name} - {item.quantity}шт")

        if obj.items.count() > 3:
            summary_parts.append(f"и ещё {obj.items.count() - 3}")

        return ", ".join(summary_parts) if summary_parts else "No items"


class CreateOrderSerializer(serializers.Serializer):
    """Serializer for creating an order from cart"""

    pass  # No input needed, will use cart items
