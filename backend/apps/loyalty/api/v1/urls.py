from django.urls import path

from apps.loyalty.api.v1.actions import ApplyPromocodeAPIView, MyLoyaltyAPIView, TopupDepositAPIView
from apps.loyalty.api.v1.views import (
    AchievementDetailAPIView,
    AchievementListCreateAPIView,
    CashbackDetailAPIView,
    CashbackListCreateAPIView,
    DiscountDetailAPIView,
    DiscountListCreateAPIView,
    PromocodeDetailAPIView,
    PromocodeListCreateAPIView,
)

app_name = "loyalty"

urlpatterns = [
    path("discounts/", DiscountListCreateAPIView.as_view(), name="discount-list"),
    path("discounts/<int:pk>/", DiscountDetailAPIView.as_view(), name="discount-detail"),
    path("promocodes/", PromocodeListCreateAPIView.as_view(), name="promocode-list"),
    path("promocodes/<int:pk>/", PromocodeDetailAPIView.as_view(), name="promocode-detail"),
    path("cashback/", CashbackListCreateAPIView.as_view(), name="cashback-list"),
    path("cashback/<int:pk>/", CashbackDetailAPIView.as_view(), name="cashback-detail"),
    path("achievements/", AchievementListCreateAPIView.as_view(), name="achievement-list"),
    path("achievements/<int:pk>/", AchievementDetailAPIView.as_view(), name="achievement-detail"),
    # Actions
    path("my-summary/", MyLoyaltyAPIView.as_view(), name="my-loyalty"),
    path("promocodes/apply/", ApplyPromocodeAPIView.as_view(), name="promocode-apply"),
    path("topup/", TopupDepositAPIView.as_view(), name="deposit-topup"),
]
