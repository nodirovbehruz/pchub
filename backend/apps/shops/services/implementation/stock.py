from apps.accounts.models import CustomUser
from apps.shops.models import Stock
from apps.shops.repositories.interface.stock import IStockRepository
from apps.shops.services.interface.stock import (
    IAddToStockService,
    IAdjustStockService,
    IRemoveFromStockService,
)


class AddToStockService(IAddToStockService):
    """Add To Stock Service"""

    def __init__(self, repository: IStockRepository):
        self.repository = repository

    def execute(self, stock: Stock, quantity: int, reason: str, user: CustomUser):
        """Add To Stock"""
        return self.repository.add_stock(stock, quantity, reason, user)


class RemoveFromStockService(IRemoveFromStockService):
    """Remove From Stock Service"""

    def __init__(self, repository: IStockRepository):
        self.repository = repository

    def execute(self, stock: Stock, quantity: int, reason: str, user: CustomUser):
        """Remove From Stock"""
        return self.repository.remove_stock(stock, quantity, reason, user)


class AdjustStockService(IAdjustStockService):
    """Adjust Stock Service"""

    def __init__(self, repository: IStockRepository):
        self.repository = repository

    def execute(self, stock: Stock, quantity: int, reason: str, user: CustomUser):
        """Adjust Stock"""
        return self.repository.adjust_stock(stock, quantity, reason, user)
