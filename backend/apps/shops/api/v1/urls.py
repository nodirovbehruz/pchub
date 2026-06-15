from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.shops.api.v1.views.cart import (
    AddSetToCartAPIView,
    AddToCartAPIView,
    CartDetailAPIView,
    ClearCartAPIView,
    RemoveFromCartAPIView,
    UpdateCartItemAPIView,
)
from apps.shops.api.v1.views.category import (
    CategoriesProductsAPIView,
    CategoryCreateAPIView,
    CategoryDestroyAPIView,
    CategoryListAPIView,
    CategoryUpdateAPIView,
)
from apps.shops.api.v1.views.order import (
    AdminOrderListAPIView,
    AdminOrderPayAPIView,
    AdminOrderStatusAPIView,
    CreateOrderAPIView,
    OrderDetailAPIView,
    OrderListAPIView,
)
from apps.shops.api.v1.views.page import CategoriesWithProductsListView, ShopPageAPIView
from apps.shops.api.v1.views.product import (
    ProductAdminDetailAPIView,
    ProductAdminListCreateAPIView,
    ProductCreateAPIView,
    ProductDestroyAPIView,
    ProductDetailAPIView,
    ProductsListAPIView,
    ProductStockAdjustAPIView,
    ProductTagViewSet,
    ProductUpdateAPIView,
)
from apps.shops.api.v1.views.sell import POSSellAPIView
from apps.shops.api.v1.views.service_combo import (
    ComboDetailAPIView, ComboListCreateAPIView,
    ServiceDetailAPIView, ServiceListCreateAPIView,
)
from apps.shops.api.v1.views.stock import (
    StockAddAPIView,
    StockAdjustAPIView,
    StockRemoveAPIView,
)

app_name = "shop"

router = DefaultRouter()

router.register(r"products", ProductTagViewSet)

category_urlpatterns = [
    path("", CategoryListAPIView.as_view(), name="category-list"),
    path("create/", CategoryCreateAPIView.as_view(), name="category-create"),
    path(
        "<slug:slug>/update/", CategoryUpdateAPIView.as_view(), name="category-update"
    ),
    path(
        "<slug:slug>/delete/", CategoryDestroyAPIView.as_view(), name="category-delete"
    ),
    path(
        "<slug:slug>/products/",
        CategoriesProductsAPIView.as_view(),
        name="category-products",
    ),
]

product_urlpatterns = [
    path("", ProductsListAPIView.as_view(), name="product-list"),
    path("create/", ProductCreateAPIView.as_view(), name="product-create"),
    path("<slug:slug>/update/", ProductUpdateAPIView.as_view(), name="product-update"),
    path("<slug:slug>/delete/", ProductDestroyAPIView.as_view(), name="product-delete"),
    path(
        "<slug:slug>/products/", ProductDetailAPIView.as_view(), name="product-detail"
    ),
]

stock_urlpatterns = [
    path("", StockAddAPIView.as_view(), name="stock-add"),
    path("remove/", StockRemoveAPIView.as_view(), name="stock-remove"),
    path("adjust/", StockAdjustAPIView.as_view(), name="stock-adjust"),
]

page_urlpatterns = [
    path("main/", ShopPageAPIView.as_view(), name="shop-page"),
    path(
        "categories/",
        CategoriesWithProductsListView.as_view(),
        name="categories-with-products",
    ),
]

cart_urlpatterns = [
    path("", CartDetailAPIView.as_view(), name="cart-detail"),
    path("add/", AddToCartAPIView.as_view(), name="cart-add"),
    path("add-set/", AddSetToCartAPIView.as_view(), name="cart-add-set"),
    path(
        "item/<int:item_id>/", UpdateCartItemAPIView.as_view(), name="cart-item-update"
    ),
    path(
        "item/<int:item_id>/remove/",
        RemoveFromCartAPIView.as_view(),
        name="cart-item-remove",
    ),
    path("clear/", ClearCartAPIView.as_view(), name="cart-clear"),
]

order_urlpatterns = [
    path("", OrderListAPIView.as_view(), name="order-list"),
    path("create/", CreateOrderAPIView.as_view(), name="order-create"),
    # Operator-facing (must precede the <int:order_id> catch-all).
    path("admin/", AdminOrderListAPIView.as_view(), name="admin-order-list"),
    path("admin/<int:order_id>/pay/", AdminOrderPayAPIView.as_view(), name="admin-order-pay"),
    path("admin/<int:order_id>/status/", AdminOrderStatusAPIView.as_view(), name="admin-order-status"),
    path("<int:order_id>/", OrderDetailAPIView.as_view(), name="order-detail"),
]


urlpatterns = [
    path(
        "categories/", include((category_urlpatterns, app_name), namespace="category")
    ),
    path("products/", include((product_urlpatterns, app_name), namespace="product")),
    path("stock/", include((stock_urlpatterns, app_name), namespace="stock")),
    path("page/", include((page_urlpatterns, app_name), namespace="page")),
    path("cart/", include((cart_urlpatterns, app_name), namespace="cart")),
    path("orders/", include((order_urlpatterns, app_name), namespace="orders")),
    # Services & Combos
    path("services/", ServiceListCreateAPIView.as_view(), name="service-list"),
    path("services/<int:pk>/", ServiceDetailAPIView.as_view(), name="service-detail"),
    path("combos/", ComboListCreateAPIView.as_view(), name="combo-list"),
    path("combos/<int:pk>/", ComboDetailAPIView.as_view(), name="combo-detail"),
    # Admin product CRUD (id-based, used by React admin panel CrudPage)
    path("admin/products/", ProductAdminListCreateAPIView.as_view(), name="product-admin-list"),
    path("admin/products/<int:pk>/", ProductAdminDetailAPIView.as_view(), name="product-admin-detail"),
    path("admin/products/<int:pk>/stock/", ProductStockAdjustAPIView.as_view(), name="product-stock-adjust"),
    # POS sell
    path("sell/", POSSellAPIView.as_view(), name="pos-sell"),
]
