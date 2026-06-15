from apps.accounts.models import CustomUser
from apps.shops.models import Stock
from apps.shops.repositories.interface.stock import IStockRepository


class StockRepository(IStockRepository):
    def __init__(self, model: Stock = Stock):
        self.model = model

    def add_stock(
        self, stock: Stock, quantity: int, reason: str, user: CustomUser
    ) -> Stock:
        """Add Stock — delegate to the model so the underflow guard + StockTransaction
        audit run (was raw arithmetic that bypassed both)."""
        stock.add_stock(quantity, reason=reason, user=user)
        return stock

    def remove_stock(
        self, stock: Stock, quantity: int, reason: str, user: CustomUser
    ) -> Stock:
        """Remove Stock — model method raises ValueError on underflow (was raw
        `quantity -= ...` that let stock go negative silently)."""
        stock.remove_stock(quantity, reason=reason, user=user)
        return stock

    def adjust_stock(
        self, stock: Stock, quantity: int, reason: str, user: CustomUser
    ) -> Stock:
        """Adjust Stock to an absolute quantity (validated by the model method)."""
        stock.adjust_stock(quantity, reason=reason, user=user)
        return stock

    def get_stock(self, stock_id: int) -> Stock:
        """Get Stock"""

        return self.model.objects.get(id=stock_id)
