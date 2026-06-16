from django.urls import path

from apps.clubs.api.v1.platform_views import (
    PlatformDashboardAPIView,
    PlatformClubsAPIView,
    PlatformClubDetailAPIView,
    PlatformClubManageAPIView,
    PlatformClubCreateAPIView,
    PlatformImpersonateAPIView,
    PlatformPlansAPIView,
    PlatformPlanDetailAPIView,
    PlatformUsersAPIView,
    PlatformUserActionAPIView,
    PlatformEmployeesAPIView,
    PlatformBillingAPIView,
)

app_name = "platform"

urlpatterns = [
    path("dashboard/", PlatformDashboardAPIView.as_view(), name="dashboard"),
    path("clubs/", PlatformClubsAPIView.as_view(), name="clubs"),
    path("clubs/create/", PlatformClubCreateAPIView.as_view(), name="club-create"),
    path("clubs/<int:pk>/", PlatformClubDetailAPIView.as_view(), name="club-detail"),
    path("clubs/<int:pk>/manage/", PlatformClubManageAPIView.as_view(), name="club-manage"),
    path("clubs/<int:pk>/impersonate/", PlatformImpersonateAPIView.as_view(), name="club-impersonate"),
    path("plans/", PlatformPlansAPIView.as_view(), name="plans"),
    path("plans/<int:pk>/", PlatformPlanDetailAPIView.as_view(), name="plan-detail"),
    path("users/", PlatformUsersAPIView.as_view(), name="users"),
    # CustomUser PK is a UUID — `<int:pk>` never matched (404 in prod).
    path("users/<uuid:pk>/action/", PlatformUserActionAPIView.as_view(), name="user-action"),
    path("employees/", PlatformEmployeesAPIView.as_view(), name="employees"),
    path("billing/", PlatformBillingAPIView.as_view(), name="billing"),
]
