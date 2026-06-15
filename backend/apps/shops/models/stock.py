from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.shops.models.enums import TransactionType


class Stock(models.Model):
    """Stock/Inventory for products"""

    product = models.OneToOneField(
        "shops.Product", on_delete=models.CASCADE, related_name="stock"
    )
    quantity = models.IntegerField(
        default=0, validators=[MinValueValidator(0)], help_text="Current stock quantity"
    )
    reserved_quantity = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Quantity reserved for orders (if implementing orders later)",
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=10, help_text="Alert when stock falls below this"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shop_stock"

    def __str__(self):
        return f"{self.product.name}: {self.quantity} in stock"

    @property
    def available_quantity(self):
        """Quantity available for sale"""
        return max(0, self.quantity - self.reserved_quantity)

    @property
    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.available_quantity <= self.low_stock_threshold

    @property
    def is_out_of_stock(self):
        """Check if out of stock"""
        return self.available_quantity <= 0

    def add_stock(self, quantity, reason="", user=None):
        """Add stock and create transaction"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        old_quantity = self.quantity
        self.quantity += quantity
        self.save()

        # Create transaction record
        StockTransaction.objects.create(
            stock=self,
            transaction_type="IN",
            quantity=quantity,
            quantity_before=old_quantity,
            quantity_after=self.quantity,
            reason=reason,
            user=user,
        )

        return self.quantity

    def remove_stock(self, quantity, reason="", user=None):
        """Remove stock and create transaction"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if self.available_quantity < quantity:
            raise ValueError(
                f"Insufficient stock. Available: {self.available_quantity}"
            )

        old_quantity = self.quantity
        self.quantity -= quantity
        self.save()

        # Create transaction record
        StockTransaction.objects.create(
            stock=self,
            transaction_type="OUT",
            quantity=quantity,
            quantity_before=old_quantity,
            quantity_after=self.quantity,
            reason=reason,
            user=user,
        )

        return self.quantity

    def adjust_stock(self, new_quantity, reason="", user=None):
        """Adjust stock to specific quantity"""
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative")

        old_quantity = self.quantity
        difference = new_quantity - old_quantity

        if difference == 0:
            return self.quantity

        self.quantity = new_quantity
        self.save()

        # Create transaction record
        StockTransaction.objects.create(
            stock=self,
            transaction_type="ADJUSTMENT",
            quantity=abs(difference),
            quantity_before=old_quantity,
            quantity_after=self.quantity,
            reason=reason,
            user=user,
        )

        return self.quantity


class StockTransaction(models.Model):
    """Track all stock movements"""

    stock = models.ForeignKey(
        Stock, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity = models.PositiveIntegerField(help_text="Quantity changed")
    quantity_before = models.IntegerField(help_text="Stock before transaction")
    quantity_after = models.IntegerField(help_text="Stock after transaction")
    reason = models.TextField(blank=True, help_text="Reason for transaction")
    reference_id = models.CharField(
        max_length=100, blank=True, help_text="Reference to order, invoice, etc."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_transactions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "shop_stock_transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["stock", "-created_at"]),
            models.Index(fields=["transaction_type", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.transaction_type}: {self.quantity} of {self.stock.product.name}"
