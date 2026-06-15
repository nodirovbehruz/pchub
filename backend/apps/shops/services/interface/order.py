from typing import List, Protocol

from django.contrib.auth import get_user_model

from apps.shops.models import Order

User = get_user_model()


class IOrderService(Protocol):
    """Interface for Order service"""

    def get_user_orders(self, user: User) -> List[Order]:
        """Get all orders for a user"""
        ...

    def get_order_detail(self, user: User, order_id: int) -> Order:
        """Get specific order details"""
        ...

    def create_order_from_cart(self, user: User) -> Order:
        """Create an order from user's cart"""
        ...
