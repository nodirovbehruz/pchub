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
    product_items = ComboProductItemSerializer(many=True, read_only=True)
    service_items = ComboServiceItemSerializer(many=True, read_only=True)

    class Meta:
        model = Combo
        fields = "__all__"
        read_only_fields = ["id", "club", "created_at", "updated_at"]  # club: no cross-tenant re-assign


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
