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
        extra_kwargs = {
            "slug": {"required": False, "allow_blank": True},
        }

    @staticmethod
    def _gen_slug(name):
        """Build a safe ASCII slug from the (possibly Cyrillic) name. SlugField rejects
        non-ASCII, so a Russian name like «Напитки» produced an invalid slug → 500/400
        on create. Strip to ASCII and fall back to a random suffix when nothing's left."""
        import re
        import uuid

        base = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
        return (base[:40] + "-" + uuid.uuid4().hex[:8]) if base else "cat-" + uuid.uuid4().hex[:12]

    def validate(self, attrs):
        # On create, always derive a valid slug from the name when the client sends none
        # (or a blank/Cyrillic one) — the frontend no longer sends slug at all.
        if self.instance is None and not attrs.get("slug"):
            attrs["slug"] = self._gen_slug(attrs.get("name"))
        return attrs


class CategoryWithProductsSerializer(CategorySerializer):
    """Category serializer with products"""

    products = ProductListSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = CategorySerializer.Meta.fields + ["products"]
        read_only_fields = ["created_at", "updated_at", "products"]
