from rest_framework import serializers

from apps.shops.api.v1.serializers.product import (
    ProductListSerializer,
    ProductSetListSerializer,
)


class ProductAndSetSerializer(serializers.Serializer):
    """Serializer for combined products and sets for the main page"""

    sets = ProductSetListSerializer(many=True, read_only=True)
    products = ProductListSerializer(many=True, read_only=True)
