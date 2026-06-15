from typing import Any, Dict, Protocol

from django.contrib.auth import get_user_model

from apps.shops.models import Cart, CartItem

User = get_user_model()


class ICartService(Protocol):
    """Interface for Cart service"""

    def get_cart(self, user: User) -> Cart:
        """Get or create cart for user"""
        ...

    def add_to_cart(self, user: User, product_id: int, quantity: int) -> Cart:
        """Add product to cart"""
        ...

    def update_cart_item(self, user: User, item_id: int, quantity: int) -> Cart:
        """Update cart item quantity"""
        ...

    def remove_from_cart(self, user: User, item_id: int) -> Cart:
        """Remove item from cart"""
        ...

    def clear_cart(self, user: User) -> Cart:
        """Clear all items from cart"""
        ...
