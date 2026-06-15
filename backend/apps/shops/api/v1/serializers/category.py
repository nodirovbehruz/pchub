from rest_framework import serializers

from apps.shops.api.v1.serializers.product import ProductListSerializer
from apps.shops.models import Category


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer"""

    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "image",
            "order",
            "is_active",
            "product_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class CategoryWithProductsSerializer(CategorySerializer):
    """Category serializer with products"""

    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = CategorySerializer.Meta.fields + ["products"]
        read_only_fields = ["created_at", "updated_at", "products"]
