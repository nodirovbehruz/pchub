from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.shops.api.v1.serializers.category import CategoryWithProductsSerializer
from apps.shops.api.v1.serializers.combined import ProductAndSetSerializer
from apps.shops.models import Category, Product, ProductSet


def shop_club_id(request):
    """Resolve the club whose catalog the shell should see. Products are tenant-
    isolated (Product.club), so the storefront MUST be scoped — otherwise a PC in
    one club sees and orders another club's products. Resolve from X-Club-Id /
    ?club= / the requesting PC's hardware_id."""
    cid = getattr(request, "current_club_id", None) or request.query_params.get("club")
    if cid:
        return cid
    hw = request.query_params.get("hardware_id")
    if hw:
        from apps.computers.models import Computer
        c = Computer.objects.filter(hardware_id=hw).first()
        if c:
            return c.club_id
    return None


class ShopPageAPIView(APIView):
    """View to get combined products and sets for the main page (club-scoped)."""

    serializer_class = ProductAndSetSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        club = shop_club_id(request)
        # Respect the «Показывать в шелле» (shell_display) toggle — was ignored, so
        # products hidden from the client still appeared in the shell storefront.
        products = Product.objects.filter(is_active=True, shell_display=True)
        sets = ProductSet.objects.filter(is_active=True)
        if club:
            products = products.filter(club_id=club)
            if any(f.name == "club" for f in ProductSet._meta.fields):
                sets = sets.filter(club_id=club)
        else:
            # No club context → show nothing rather than leak every club's catalog.
            products = products.none()
            sets = sets.none()

        serializer = ProductAndSetSerializer(
            {"sets": sets.order_by("-created_at")[:2], "products": products.order_by("?")[:9]},
            context={"request": request},
        )
        return Response(serializer.data)


@extend_schema(tags=["Shop - Pages"])
class CategoriesWithProductsListView(generics.ListAPIView):
    """List categories with their products — scoped to the requesting PC's club."""

    serializer_class = CategoryWithProductsSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        club = shop_club_id(self.request)
        prod_qs = Product.objects.filter(is_active=True, shell_display=True)
        prod_qs = prod_qs.filter(club_id=club) if club else prod_qs.none()
        # Only categories that have products in THIS club, with products prefetched
        # already filtered to this club so the serializer can't expose foreign ones.
        return (
            Category.objects.filter(products__in=prod_qs).distinct()
            .prefetch_related(Prefetch("products", queryset=prod_qs))
        )
