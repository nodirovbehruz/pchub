from rest_framework import serializers

from apps.shops.api.v1.serializers.stock import StockInfoSerializer
from apps.shops.models import (
    Product,
    ProductImage,
    ProductSet,
    ProductSetItem,
    ProductTag,
)


class ProductTagSerializer(serializers.ModelSerializer):
    """Product tag serializer"""

    class Meta:
        model = ProductTag
        fields = ["id", "name", "slug", "color"]


class ProductImageSerializer(serializers.ModelSerializer):
    """Product image serializer"""

    class Meta:
        model = ProductImage
        fields = ["id", "image", "order"]


class ProductListSerializer(serializers.ModelSerializer):
    """Product list serializer"""

    tags = ProductTagSerializer(many=True, read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    current_stock = serializers.IntegerField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "category",
            "tags",
            "price",
            "original_price",
            "discount_percentage",
            "main_image",
            "is_featured",
            "in_stock",
            "current_stock",
        ]

    def get_main_image(self, obj):
        if obj.main_image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.main_image.url) if request else obj.main_image.url
        return f"https://picsum.photos/seed/product-{obj.id}/400/300"


class ProductDetailSerializer(serializers.ModelSerializer):
    """Product detail serializer"""

    category_name = serializers.CharField(source="category.name", read_only=True)
    tags = ProductTagSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    stock = StockInfoSerializer(read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "short_description",
            "category",
            "category_name",
            "tags",
            "price",
            "original_price",
            "has_discount",
            "discount_percentage",
            "main_image",
            "images",
            "is_active",
            "is_featured",
            "sku",
            "barcode",
            "stock",
            "in_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ProductSetItemSerializer(serializers.ModelSerializer):
    """Product set item serializer"""

    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source="product", write_only=True
    )
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = ProductSetItem
        fields = ["id", "product", "product_id", "quantity", "order", "subtotal"]


class ProductSetListSerializer(serializers.ModelSerializer):
    """Product set list serializer"""

    total_items = serializers.IntegerField(read_only=True)
    savings = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    savings_percentage = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductSet
        fields = [
            "id",
            "name",
            "slug",
            "short_description",
            "price",
            "original_price",
            "savings",
            "savings_percentage",
            "main_image",
            "is_featured",
            "total_items",
            "in_stock",
        ]


class ProductSetDetailSerializer(serializers.ModelSerializer):
    """Product set detail serializer"""

    items = ProductSetItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    savings = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    savings_percentage = serializers.IntegerField(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductSet
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "short_description",
            "price",
            "original_price",
            "savings",
            "savings_percentage",
            "main_image",
            "is_active",
            "is_featured",
            "items",
            "total_items",
            "in_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
