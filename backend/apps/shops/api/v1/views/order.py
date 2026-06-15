from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shops.api.v1.serializers.order import OrderSerializer
from apps.shops.services.implementation.order import OrderService


@extend_schema(tags=["Shop - Orders"])
class OrderListAPIView(APIView):
    """List user's orders"""

    permission_classes = [IsAuthenticated]
    service = OrderService()

    def get(self, request):
        """Get all orders for the current user"""
        orders = self.service.get_user_orders(request.user)
        serializer = OrderSerializer(orders, many=True, context={"request": request})
        return Response(serializer.data)


@extend_schema(tags=["Shop - Orders"])
class CreateOrderAPIView(APIView):
    """Create an order from cart"""

    permission_classes = [IsAuthenticated]
    service = OrderService()

    def post(self, request):
        """Create an order from the user's cart"""
        hardware_id = request.data.get("hardware_id") if isinstance(request.data, dict) else None
        order = self.service.create_order_from_cart(request.user, hardware_id=hardware_id)
        serializer = OrderSerializer(order, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Shop - Orders"])
class OrderDetailAPIView(APIView):
    """Get order details"""

    permission_classes = [IsAuthenticated]
    service = OrderService()

    def get(self, request, order_id):
        """Get specific order details"""
        order = self.service.get_order_detail(user=request.user, order_id=order_id)
        serializer = OrderSerializer(order, context={"request": request})
        return Response(serializer.data)


# ── Admin / operator order management ─────────────────────────────────────────

def _operator_can(user, club_id):
    """Club owner / manager / platform admin may manage a club's orders."""
    if getattr(user, "is_admin", False) or getattr(user, "user_type", "") == "admin":
        return True
    if not club_id:
        return False
    from apps.clubs.models import Club, ClubMembership
    return Club.objects.filter(id=club_id, owner=user).exists() or ClubMembership.objects.filter(
        user=user, club_id=club_id, is_active=True, role__in=["owner", "manager", "operator"]
    ).exists()


@extend_schema(tags=["Shop - Orders"])
class AdminOrderListAPIView(APIView):
    """Operator: incoming orders for a club (queue), newest first.
    GET ?club=<id>&status=PENDING|PROCESSING|COMPLETED|CANCELLED (status optional)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.shops.models import Order
        club_id = getattr(request, "current_club_id", None) or request.query_params.get("club")
        if not _operator_can(request.user, club_id):
            return Response({"error": "Нет прав на заказы этого клуба"}, status=status.HTTP_403_FORBIDDEN)
        qs = (Order.objects.filter(computer__club_id=club_id)
              .select_related("account", "computer").prefetch_related("items__product")
              .order_by("-created_at"))
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        serializer = OrderSerializer(qs[:200], many=True, context={"request": request})
        return Response(serializer.data)


@extend_schema(tags=["Shop - Orders"])
class AdminOrderPayAPIView(APIView):
    """Operator confirms payment for an order → records a Payment and moves it to
    PROCESSING (being prepared). POST body: { payment_method: cash|card|transfer|deposit }."""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        from decimal import Decimal
        from django.db import transaction
        from apps.shops.models import Order
        from apps.billing.models import Payment, PaymentMethod

        try:
            order = Order.objects.select_related("computer", "account").get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)

        club_id = getattr(order.computer, "club_id", None)
        if not _operator_can(request.user, club_id):
            return Response({"error": "Нет прав на этот заказ"}, status=status.HTTP_403_FORBIDDEN)
        if order.status in ("COMPLETED", "CANCELLED"):
            return Response({"error": f"Заказ уже {order.status}"}, status=status.HTTP_400_BAD_REQUEST)

        method = (request.data.get("payment_method") or "cash").lower()
        # BUGFIX: 'deposit' must NOT map to CASH — paying from the client's deposit puts
        # no physical cash in the drawer, but recording it as CASH inflated the shift
        # Z-report (expected_cash) and produced a phantom shortage. Mirror the POS path
        # (sell.py): deposit → TRANSFER + a [DEPOSIT] note so the shift cash total and
        # refund/dashboard logic correctly exclude/recognize it.
        method_map = {
            "cash": PaymentMethod.CASH, "card": PaymentMethod.CARD,
            "transfer": PaymentMethod.TRANSFER, "deposit": PaymentMethod.TRANSFER,
        }
        pay_note = (f"[DEPOSIT][SHOP] Заказ #{order.id}" if method == "deposit"
                    else f"[SHOP] Заказ #{order.id}")

        # BUGFIX: deposit deduction and Payment creation were NOT atomic — a crash
        # between them would debit the client but create no payment record (lost money).
        # Wrap the entire pay flow in a single transaction with select_for_update.
        with transaction.atomic():
            # If paying from the client's club deposit, debit it (real money).
            if method == "deposit" and order.account_id:
                from apps.clubs.models import UserClubProfile
                prof = UserClubProfile.objects.select_for_update().filter(
                    user=order.account, club_id=club_id
                ).first()
                if not prof or prof.deposit_money < order.total_price:
                    return Response({"error": "Недостаточно средств на депозите"}, status=status.HTTP_400_BAD_REQUEST)
                prof.deposit_money -= order.total_price
                prof.save(update_fields=["deposit_money"])

            payment = Payment.objects.create(
                user=order.account, admin=request.user, computer=order.computer,
                amount_paid=Decimal(str(order.total_price)), minutes_added=0,
                payment_method=method_map.get(method, PaymentMethod.CASH),
                note=pay_note, club_id=club_id,
            )

            order.status = "PROCESSING"
            order.save(update_fields=["status", "updated_at"])

        # Itemized OperationLog so the order shows up in the dashboard's
        # "Проданные товары" (which reads PAYMENT_CREATE logs with kind=products).
        try:
            from apps.billing.models import OperationLog, LogAction
            OperationLog.objects.create(
                club_id=club_id,
                subject=request.user if request.user.is_authenticated else None,
                object_type="Payment", object_id=str(payment.id),
                object_repr=f"Заказ из шелла #{order.id} — {order.total_price}сум",
                action=LogAction.PAYMENT_CREATE,
                payload={
                    "items": [
                        {"kind": "products", "id": oi.product_id, "name": oi.product.name,
                         "qty": oi.quantity, "price": str(oi.price)}
                        for oi in order.items.all()
                    ],
                    "method": method, "total": str(order.total_price),
                    "source": "shop_order", "order_id": order.id,
                },
            )
        except Exception:
            pass

        _notify_client_order(order, "Заказ оплачен — готовим 👨‍🍳")
        return Response({"success": True, "status": order.status, "order_id": order.id})


@extend_schema(tags=["Shop - Orders"])
class AdminOrderStatusAPIView(APIView):
    """Operator advances an order: PROCESSING → COMPLETED (delivered) or CANCELLED.
    POST body: { status: PROCESSING|COMPLETED|CANCELLED }. Cancel restores stock."""

    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        from apps.shops.models import Order

        try:
            order = Order.objects.select_related("computer", "account").prefetch_related("items__product").get(id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)

        club_id = getattr(order.computer, "club_id", None)
        if not _operator_can(request.user, club_id):
            return Response({"error": "Нет прав на этот заказ"}, status=status.HTTP_403_FORBIDDEN)

        new_status = (request.data.get("status") or "").upper()
        if new_status not in ("PROCESSING", "COMPLETED", "CANCELLED"):
            return Response({"error": "Недопустимый статус"}, status=status.HTTP_400_BAD_REQUEST)

        # Cancelling returns the reserved stock AND refunds a deposit-paid order
        # (was restoring stock only → client paid from deposit, order cancelled,
        # money never returned).
        if new_status == "CANCELLED" and order.status != "CANCELLED":
            from django.db import transaction as _txn
            was_paid = order.status == "PROCESSING"
            with _txn.atomic():
                for it in order.items.all():
                    try:
                        st = it.product.stock
                        st.quantity += it.quantity
                        st.save(update_fields=["quantity"])
                    except Exception:
                        pass
                # Refund the deposit if this order was paid from the client's deposit.
                if was_paid and order.account_id and club_id:
                    try:
                        from apps.billing.models import Payment
                        from apps.clubs.models import UserClubProfile
                        pay = (Payment.objects.filter(
                            user_id=order.account_id, club_id=club_id,
                            note__icontains=f"[DEPOSIT][SHOP] Заказ #{order.id}")
                            .exclude(note__icontains="[REFUNDED]").first())
                        if pay:
                            prof = UserClubProfile.objects.select_for_update().filter(
                                user_id=order.account_id, club_id=club_id).first()
                            if prof:
                                prof.deposit_money = (prof.deposit_money or 0) + pay.amount_paid
                                prof.save(update_fields=["deposit_money"])
                                pay.note = f"[REFUNDED] {pay.note}".strip()
                                pay.save(update_fields=["note"])
                    except Exception:
                        pass
                order.status = new_status
                order.save(update_fields=["status", "updated_at"])
        else:
            order.status = new_status
            order.save(update_fields=["status", "updated_at"])
        labels = {"PROCESSING": "Готовим 👨‍🍳", "COMPLETED": "Доставлено ✅", "CANCELLED": "Заказ отменён"}
        _notify_client_order(order, labels.get(new_status, new_status))
        return Response({"success": True, "status": order.status, "order_id": order.id})


def _notify_client_order(order, message):
    """Push the new order status to the client's shell (best-effort)."""
    try:
        if not order.account_id:
            return
        from realtime.broadcast import push_order_status
        push_order_status(order.account_id, {
            "order_id": order.id, "status": order.status, "message": message,
        })
    except Exception:
        pass
