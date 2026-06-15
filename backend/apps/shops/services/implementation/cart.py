from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from apps.shops.models import Cart, CartItem, Product
from apps.shops.services.interface.cart import ICartService

User = get_user_model()


class CartService(ICartService):
    """Service for Cart management"""

    def get_cart(self, user: User) -> Cart:
        """Get or create cart for user"""
        cart, _ = Cart.objects.get_or_create(account=user)
        return cart

    def add_to_cart(self, user: User, product_id: int, quantity: int) -> Cart:
        """Add product to cart"""
        # Get or create cart
        cart, _ = Cart.objects.get_or_create(account=user)

        # Get product
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            raise ValidationError({"product_id": "Product not found"})

        # Check stock
        if product.current_stock < quantity:
            raise ValidationError(
                {
                    "quantity": f"Insufficient stock. Only {product.current_stock} available."
                }
            )

        # Add or update cart item
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, defaults={"quantity": quantity}
        )

        if not created:
            # Item already in cart, update quantity
            cart_item.quantity += quantity
            # Check stock again
            if product.current_stock < cart_item.quantity:
                raise ValidationError(
                    {
                        "quantity": f"Insufficient stock. Only {product.current_stock} available."
                    }
                )
            cart_item.save()

        return cart

    def update_cart_item(self, user: User, item_id: int, quantity: int) -> Cart:
        """Update cart item quantity"""
        try:
            cart_item = CartItem.objects.get(id=item_id, cart__account=user)
        except CartItem.DoesNotExist:
            raise ValidationError({"item_id": "Cart item not found"})

        cart = cart_item.cart

        # If quantity is 0, delete the item
        if quantity == 0:
            cart_item.delete()
        else:
            # Check stock
            if cart_item.product.current_stock < quantity:
                raise ValidationError(
                    {
                        "quantity": f"Insufficient stock. Only {cart_item.product.current_stock} available."
                    }
                )
            cart_item.quantity = quantity
            cart_item.save()

        return cart

    def remove_from_cart(self, user: User, item_id: int) -> Cart:
        """Remove item from cart"""
        try:
            cart_item = CartItem.objects.get(id=item_id, cart__account=user)
        except CartItem.DoesNotExist:
            raise ValidationError({"item_id": "Cart item not found"})

        cart = cart_item.cart
        cart_item.delete()

        return cart

    def clear_cart(self, user: User) -> Cart:
        """Clear all items from cart"""
        cart, _ = Cart.objects.get_or_create(account=user)
        cart.items.all().delete()
        return cart
