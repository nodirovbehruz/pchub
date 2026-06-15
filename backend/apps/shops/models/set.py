from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ProductSet(models.Model):
    """A set of products"""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=255, blank=True)

    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Bundle price",
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Total price if bought separately (for showing savings)",
    )

    # Images
    main_image = models.ImageField(upload_to="sets/", blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # Ordering
    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shop_product_sets"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    @property
    def savings(self):
        """Calculate savings amount"""
        if self.original_price and self.original_price > self.price:
            return self.original_price - self.price
        return Decimal("0.00")

    @property
    def savings_percentage(self):
        """Calculate savings percentage"""
        if self.original_price and self.original_price > 0:
            return int((self.savings / self.original_price) * 100)
        return 0

    @property
    def total_items(self):
        """Get total number of items in set"""
        return self.items.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def in_stock(self):
        """Check if all items in set are in stock"""
        for item in self.items.all():
            if item.product.current_stock < item.quantity:
                return False
        return True

    def calculate_original_price(self):
        """Auto-calculate original price from items"""
        total = Decimal("0.00")
        for item in self.items.select_related("product").all():
            total += item.product.price * item.quantity
        return total


class ProductSetItem(models.Model):
    """Items within a product set"""

    product_set = models.ForeignKey(
        ProductSet, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey(
        "shops.Product", on_delete=models.CASCADE, related_name="set_items"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="How many of this product in the set",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "shop_product_set_items"
        ordering = ["order"]
        unique_together = [["product_set", "product"]]

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.product_set.name}"

    @property
    def subtotal(self):
        """Calculate subtotal for this item"""
        return self.product.price * self.quantity
