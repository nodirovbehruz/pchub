from typing import Protocol

from apps.accounts.models import CustomUser
from apps.shops.models import Stock


class IAddToStockService(Protocol):
    def execute(self, stock: Stock, quantity: int, reason: str, user: CustomUser):
        """Add To Stock"""


class IRemoveFromStockService(Protocol):
    def execute(self, stock: Stock, quantity: int, reason: str, user: CustomUser):
        """Remove Stock"""


class IAdjustStockService(Protocol):
    def execute(self, stock: Stock, quantity: int, reason: str, user: CustomUser):
        """Adjust Stock"""


class IGetStockService(Protocol):
    def execute(self, stock_id: int):
        """Get Stock"""
