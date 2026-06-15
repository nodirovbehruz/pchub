from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Cart(models.Model):
    """Shopping cart for users"""

    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        help_text=_("User account"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    def __str__(self):
        return f"Cart for {self.account.username}"

    @property
    def total_items(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        """Calculate total price of all items in cart"""
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    """Individual item in shopping cart"""

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        help_text=_("Shopping cart"),
    )
    product = models.ForeignKey(
        "shops.Product",
        on_delete=models.CASCADE,
        related_name="cart_items",
        help_text=_("Product"),
    )
    quantity = models.PositiveIntegerField(default=1, help_text=_("Quantity"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_items"
        verbose_name = _("Cart Item")
        verbose_name_plural = _("Cart Items")
        unique_together = [["cart", "product"]]

    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

    @property
    def subtotal(self):
        """Calculate subtotal for this item"""
        return self.product.price * self.quantity
