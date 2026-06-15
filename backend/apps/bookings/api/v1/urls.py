from django.urls import path

from apps.bookings.api.v1.views import (
    BookingDetailAPIView,
    BookingListCreateAPIView,
    BookingRedeemAPIView,
)

app_name = "bookings"

urlpatterns = [
    path("", BookingListCreateAPIView.as_view(), name="list-create"),
    path("redeem/", BookingRedeemAPIView.as_view(), name="redeem"),
    path("<int:pk>/", BookingDetailAPIView.as_view(), name="detail"),
]
