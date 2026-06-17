"""Service & Combo CRUD + POS sell endpoint registration helpers."""
from rest_framework import generics, permissions, serializers

from apps.clubs.api.v1.mixins import TenantFilterMixin, TenantCreateMixin
from apps.shops.models import Combo, ComboProductItem, ComboServiceItem, Service


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"
        read_only_fields = ["id", "club", "created_at", "updated_at"]  # club: no cross-tenant re-assign


class ComboProductItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = ComboProductItem
        fields = ["id", "product", "product_name", "qty"]


class ComboServiceItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = ComboServiceItem
        fields = ["id", "service", "service_name", "qty"]


class ComboSerializer(serializers.ModelSerializer):
    computer_group_name = serializers.CharField(source="computer_group.name", read_only=True, default=None)
    tariff_name = serializers.CharField(source="tariff.name", read_only=True, default=None)
    # WRITABLE nested items — were read_only, so the admin form's product/service rows
    # were silently dropped and every combo saved EMPTY. Now persisted on create/update.
    product_items = ComboProductItemSerializer(many=True, required=False)
    service_items = ComboServiceItemSerializer(many=True, required=False)

    class Meta:
        model = Combo
        fields = "__all__"
        read_only_fields = ["id", "club", "created_at", "updated_at"]  # club: no cross-tenant re-assign

    def _sync_items(self, combo, product_items, service_items, replace=False):
        from rest_framework.exceptions import ValidationError
        if replace:
            combo.product_items.all().delete()
            combo.service_items.all().delete()
        for it in (product_items or []):
            prod = it["product"]
            # Tenant safety: a combo must only bundle its OWN club's products.
            if combo.club_id and getattr(prod, "club_id", None) and prod.club_id != combo.club_id:
                raise ValidationError({"product_items": "Товар не принадлежит этому клубу"})
            ComboProductItem.objects.create(combo=combo, product=prod, qty=it.get("qty", 1) or 1)
        for it in (service_items or []):
            svc = it["service"]
            if combo.club_id and getattr(svc, "club_id", None) and svc.club_id != combo.club_id:
                raise ValidationError({"service_items": "Услуга не принадлежит этому клубу"})
            ComboServiceItem.objects.create(combo=combo, service=svc, qty=it.get("qty", 1) or 1)

    def create(self, validated_data):
        product_items = validated_data.pop("product_items", [])
        service_items = validated_data.pop("service_items", [])
        combo = super().create(validated_data)
        self._sync_items(combo, product_items, service_items)
        return combo

    def update(self, instance, validated_data):
        product_items = validated_data.pop("product_items", None)
        service_items = validated_data.pop("service_items", None)
        combo = super().update(instance, validated_data)
        if product_items is not None or service_items is not None:
            self._sync_items(combo, product_items, service_items, replace=True)
        return combo


class ServiceListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Service.objects.all()


class ServiceDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Service.objects.all()


class ComboListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = ComboSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Combo.objects.all().prefetch_related("product_items", "service_items")


class ComboDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ComboSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Combo.objects.all().prefetch_related("product_items", "service_items")
