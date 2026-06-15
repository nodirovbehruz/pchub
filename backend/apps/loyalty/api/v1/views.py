from rest_framework import generics, permissions

from apps.clubs.api.v1.mixins import TenantFilterMixin, TenantCreateMixin
from apps.loyalty.api.v1.serializers import (
    AchievementSerializer,
    CashbackRuleSerializer,
    DiscountSerializer,
    PromocodeSerializer,
)
from apps.loyalty.models import Achievement, CashbackRule, Discount, Promocode


class DiscountListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = DiscountSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Discount.objects.all()


class DiscountDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DiscountSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Discount.objects.all()


class PromocodeListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = PromocodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Promocode.objects.all().prefetch_related("specific_clients")


class PromocodeDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PromocodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Promocode.objects.all()


class CashbackListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = CashbackRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CashbackRule.objects.all()


class CashbackDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CashbackRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CashbackRule.objects.all()


class AchievementListCreateAPIView(TenantCreateMixin, TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Achievement.objects.all()


class AchievementDetailAPIView(TenantFilterMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AchievementSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Achievement.objects.all()
