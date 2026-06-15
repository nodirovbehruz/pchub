from django.urls import path

from apps.sessions_.api.v1.views import (
    AdminCallAnswerAPIView,
    AdminCallListCreateAPIView,
    ClientSessionDetailAPIView,
    ClientSessionListAPIView,
    ReviewListAPIView,
    ReviewMarkReadAPIView,
)

app_name = "sessions"

urlpatterns = [
    path("", ClientSessionListAPIView.as_view(), name="session-list"),
    path("<int:pk>/", ClientSessionDetailAPIView.as_view(), name="session-detail"),
    path("reviews/", ReviewListAPIView.as_view(), name="review-list"),
    path("reviews/<int:pk>/read/", ReviewMarkReadAPIView.as_view(), name="review-read"),
    path("admin-calls/", AdminCallListCreateAPIView.as_view(), name="admin-call-list"),
    path("admin-calls/<int:pk>/answer/", AdminCallAnswerAPIView.as_view(), name="admin-call-answer"),
]
