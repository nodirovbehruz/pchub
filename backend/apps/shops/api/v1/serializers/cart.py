from rest_framework import serializers

from apps.shops.models import Cart, CartItem, Product


class CartItemProductSerializer(serializers.ModelSerializer):
    """Simplified product serializer for cart items"""

    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "image", "current_stock"]

    def get_image(self, obj):
        """Product image for the cart row. Prefer `main_image` (the same field the
        shop grid shows) and fall back to the first extra `images` entry — the old
        code only checked `images`, which is usually empty, so carts had no photo."""
        img = None
        if getattr(obj, "main_image", None):
            img = obj.main_image
        else:
            first_image = obj.images.first()
            if first_image and first_image.image:
                img = first_image.image
        if not img:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(img.url) if request else img.url


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for cart items"""

    product = CartItemProductSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "subtotal", "created_at"]
        read_only_fields = ["id", "subtotal", "created_at"]


class CartSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart"""

    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "total_price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AddToCartSerializer(serializers.Serializer):
    """Serializer for adding items to cart"""

    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)

    def validate_product_id(self, value):
        """Check if product exists"""
        try:
            Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializer for updating cart item quantity"""

    quantity = serializers.IntegerField(required=True, min_value=0)
