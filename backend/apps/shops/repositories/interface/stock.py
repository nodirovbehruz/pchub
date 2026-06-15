from typing import Protocol

from apps.accounts.models import CustomUser
from apps.shops.models import Stock


class IStockRepository(Protocol):
    """Stock Repository"""

    def add_stock(
        self, stock: Stock, quantity: int, reason: str, user: CustomUser
    ) -> Stock:
        """Add Stock"""

    def remove_stock(
        self, stock: Stock, quantity: int, reason: str, user: CustomUser
    ) -> Stock:
        """Remove Stock"""

    def adjust_stock(
        self, stock: Stock, quantity: int, reason: str, user: CustomUser
    ) -> Stock:
        """Adjust Stock"""

    def get_stock(self, stock_id: int) -> Stock:
        """Get Stock"""
