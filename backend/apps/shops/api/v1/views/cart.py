from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shops.api.v1.serializers.cart import (
    AddToCartSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)
from apps.shops.services.implementation.cart import CartService


@extend_schema(tags=["Shop - Cart"])
class CartDetailAPIView(APIView):
    """Get user's shopping cart"""

    permission_classes = [IsAuthenticated]
    service = CartService()

    def get(self, request):
        """Get current user's cart"""
        cart = self.service.get_cart(request.user)
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)


@extend_schema(tags=["Shop - Cart"])
class AddToCartAPIView(APIView):
    """Add item to cart"""

    permission_classes = [IsAuthenticated]
    service = CartService()

    def post(self, request):
        """Add product to cart or update quantity if already exists"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.service.add_to_cart(
            user=request.user,
            product_id=serializer.validated_data["product_id"],
            quantity=serializer.validated_data["quantity"],
        )

        cart_serializer = CartSerializer(cart, context={"request": request})
        return Response(cart_serializer.data)


@extend_schema(tags=["Shop - Cart"])
class AddSetToCartAPIView(APIView):
    """Add a ProductSet (bundle) to the cart by expanding it into its component
    products. The cart model only holds products, so the shell used to POST the
    set's id to /cart/add/ as a product_id — which silently added an UNRELATED
    product whose id happened to match. This resolves the set's items instead.
    """

    permission_classes = [IsAuthenticated]
    service = CartService()

    def post(self, request):
        from rest_framework import status
        from apps.shops.models import ProductSet

        set_id = request.data.get("set_id") or request.data.get("product_id")
        try:
            set_qty = int(request.data.get("quantity", 1) or 1)
        except (TypeError, ValueError):
            set_qty = 1
        if not set_id:
            return Response({"error": "set_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            pset = ProductSet.objects.prefetch_related("items__product").get(id=set_id, is_active=True)
        except ProductSet.DoesNotExist:
            return Response({"error": "Набор не найден"}, status=status.HTTP_404_NOT_FOUND)

        items = list(pset.items.all())
        if not items:
            return Response({"error": "Набор пуст"}, status=status.HTTP_400_BAD_REQUEST)

        cart = None
        for item in items:
            cart = self.service.add_to_cart(
                user=request.user,
                product_id=item.product_id,
                quantity=item.quantity * set_qty,
            )

        cart_serializer = CartSerializer(cart, context={"request": request})
        return Response(cart_serializer.data)


@extend_schema(tags=["Shop - Cart"])
class UpdateCartItemAPIView(APIView):
    """Update cart item quantity"""

    permission_classes = [IsAuthenticated]
    service = CartService()

    def patch(self, request, item_id):
        """Update quantity of cart item"""
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = self.service.update_cart_item(
            user=request.user,
            item_id=item_id,
            quantity=serializer.validated_data["quantity"],
        )

        cart_serializer = CartSerializer(cart, context={"request": request})
        return Response(cart_serializer.data)


@extend_schema(tags=["Shop - Cart"])
class RemoveFromCartAPIView(APIView):
    """Remove item from cart"""

    permission_classes = [IsAuthenticated]
    service = CartService()

    def delete(self, request, item_id):
        """Remove item from cart"""
        cart = self.service.remove_from_cart(user=request.user, item_id=item_id)
        cart_serializer = CartSerializer(cart, context={"request": request})
        return Response(cart_serializer.data)


@extend_schema(tags=["Shop - Cart"])
class ClearCartAPIView(APIView):
    """Clear all items from cart"""

    permission_classes = [IsAuthenticated]
    service = CartService()

    def delete(self, request):
        """Clear all items from cart"""
        cart = self.service.clear_cart(user=request.user)
        cart_serializer = CartSerializer(cart, context={"request": request})
        return Response(cart_serializer.data)
