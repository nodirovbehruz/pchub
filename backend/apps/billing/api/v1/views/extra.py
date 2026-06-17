from decimal import Decimal

from rest_framework import generics, permissions
from rest_framework import serializers as drf_serializers

from apps.billing.models import CashOrder, OperationLog
from apps.clubs.api.v1.mixins import TenantFilterMixin, validated_club_id


class CashOrderSerializer(drf_serializers.ModelSerializer):
    signed_amount = drf_serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True,
    )
    # A negative ПКО/РКО amount poisoned the shift Z-report (expected_cash) and hid a
    # real cash shortage. Require a strictly positive amount.
    amount = drf_serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"),
    )

    class Meta:
        model = CashOrder
        fields = "__all__"
        # club/shift/admin are bound SERVER-SIDE in perform_create — the client only
        # sends {type, amount, comment}. They were required NOT-NULL FKs, so the
        # serializer rejected the create with 400 before save. Make them read-only.
        read_only_fields = ["id", "created_at", "signed_amount", "club", "shift", "admin"]


class OperationLogSerializer(drf_serializers.ModelSerializer):
    subject_username = drf_serializers.CharField(source="subject.username", read_only=True)

    class Meta:
        model = OperationLog
        fields = [
            "id", "club", "shift",
            "subject", "subject_username",
            "object_type", "object_id", "object_repr",
            "action", "payload",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CashOrderListCreateAPIView(TenantFilterMixin, generics.ListCreateAPIView):
    serializer_class = CashOrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = CashOrder.objects.all().select_related("shift", "admin")

    def perform_create(self, serializer):
        from rest_framework.exceptions import PermissionDenied, ValidationError
        from apps.billing.models import Shift, OperationLog, LogAction, CashOrderType
        cid = validated_club_id(self.request)
        if not cid:
            raise PermissionDenied("Нет доступа к клубу")
        # A cash order belongs to the club's OPEN shift. Without one, give a clear 400
        # (the FK is NOT NULL, so saving with no shift would otherwise 500).
        sh = Shift.objects.filter(club_id=cid, is_active=True).order_by("-id").first()
        if not sh:
            raise ValidationError({"shift": "Сначала откройте смену — кассовый ордер привязывается к смене"})
        serializer.validated_data.pop("club", None)
        order = serializer.save(club_id=cid, shift=sh, admin=self.request.user)
        # Mirror to the audit log so it shows on the Logs page (cash.pko / cash.rko).
        try:
            action = LogAction.CASH_PKO if order.type == CashOrderType.INCOME else LogAction.CASH_RKO
            OperationLog.objects.create(
                club_id=cid, shift=sh, subject=self.request.user,
                object_type="CashOrder", object_id=str(order.id),
                object_repr=f"{order.get_type_display()} {order.amount}сум" + (f" — {order.comment}" if order.comment else ""),
                action=action, payload={"amount": str(order.amount), "type": order.type},
            )
        except Exception:
            pass


class OperationLogListAPIView(TenantFilterMixin, generics.ListAPIView):
    serializer_class = OperationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = OperationLog.objects.all().select_related("subject", "shift")

    def get_queryset(self):
        qs = super().get_queryset()
        # Filters
        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)
        from_dt = self.request.query_params.get("from")
        to_dt = self.request.query_params.get("to")
        if from_dt:
            qs = qs.filter(created_at__gte=from_dt)
        if to_dt:
            qs = qs.filter(created_at__lte=to_dt)
        search = self.request.query_params.get("q")
        if search:
            qs = qs.filter(object_repr__icontains=search)
        return qs
