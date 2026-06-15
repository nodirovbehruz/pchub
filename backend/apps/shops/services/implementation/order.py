from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.shops.models import Cart, Order, OrderItem
from apps.shops.services.interface.order import IOrderService

User = get_user_model()


class OrderService(IOrderService):
    """Service for Order management"""

    def get_user_orders(self, user: User) -> List[Order]:
        """Get all orders for a user"""
        return Order.objects.filter(account=user).prefetch_related("items__product")

    def get_order_detail(self, user: User, order_id: int) -> Order:
        """Get specific order details"""
        try:
            return Order.objects.get(id=order_id, account=user)
        except Order.DoesNotExist:
            raise ValidationError({"order_id": "Order not found"})

    @staticmethod
    def _resolve_computer(user, hardware_id=None):
        """The PC the client is actually sitting at (so staff know where to deliver).
        Priority: explicit hardware_id → guest-pc-<id> username → user's active
        session hardware → legacy owner lookup."""
        from apps.computers.models import Computer
        if hardware_id:
            c = Computer.objects.filter(hardware_id=hardware_id).first()
            if c:
                return c
        uname = getattr(user, "username", "") or ""
        if uname.startswith("guest-pc-"):
            try:
                return Computer.objects.filter(id=int(uname.rsplit("-", 1)[1])).first()
            except (ValueError, IndexError):
                pass
        hw = getattr(user, "active_hardware_id", "") or ""
        if hw:
            c = Computer.objects.filter(hardware_id=hw).first()
            if c:
                return c
        return Computer.objects.filter(owner=user).first()

    @transaction.atomic
    def create_order_from_cart(self, user: User, hardware_id=None) -> Order:
        """Create an order from user's cart"""
        try:
            cart = Cart.objects.get(account=user)
        except Cart.DoesNotExist:
            raise ValidationError({"cart": "Cart not found"})

        if not cart.items.exists():
            raise ValidationError({"cart": "Cart is empty"})

        # Calculate total
        total_price = sum(item.subtotal for item in cart.items.all())

        # The PC the client is sitting at — so staff know where to deliver.
        computer = self._resolve_computer(user, hardware_id)
        club_id = getattr(computer, "club_id", None)

        # Tenant guard: refuse products that don't belong to this PC's club, so a
        # crafted request can't order another club's catalog.
        if club_id:
            for cart_item in cart.items.all():
                pc_club = getattr(cart_item.product, "club_id", None)
                if pc_club and pc_club != club_id:
                    raise ValidationError(
                        {"product": f"«{cart_item.product.name}» недоступен в этом клубе"}
                    )

        # Create order
        order = Order.objects.create(
            account=user, computer=computer, total_price=total_price, status="PENDING"
        )

        # Create order items from cart items
        from apps.shops.models import Stock
        for cart_item in cart.items.all():
            # Lock the stock row and validate UNDER the lock — the old check-then-
            # deduct (no select_for_update) let two concurrent checkouts both pass on
            # the last unit and oversell, and `except: pass` silently swallowed any
            # deduction error, committing the order without decrementing stock.
            stock = Stock.objects.select_for_update().filter(product=cart_item.product).first()
            available = stock.quantity if stock else 0
            if available < cart_item.quantity:
                raise ValidationError(
                    {"stock": f"Insufficient stock for {cart_item.product.name}"}
                )

            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price,
            )

            if stock:
                stock.quantity -= cart_item.quantity
                stock.save(update_fields=["quantity"])

        # Clear cart
        cart.items.all().delete()

        # Notify the club operators in realtime: a new order is waiting (with the
        # PC label + items) so the bar/counter can prepare and confirm payment.
        try:
            club_id = getattr(computer, "club_id", None)
            if club_id:
                from realtime.broadcast import push_order
                pc_label = computer.name if computer else "—"
                items_txt = ", ".join(
                    f"{oi.product.name}×{oi.quantity}" for oi in order.items.all()
                )
                push_order(club_id, {
                    "order_id": order.id,
                    "computer": pc_label,
                    "computer_id": getattr(computer, "id", None),
                    "client": getattr(user, "username", ""),
                    "items": items_txt,
                    "total": str(total_price),
                    "status": "PENDING",
                })
        except Exception:
            pass  # realtime is best-effort; the admin queue also polls

        return order
