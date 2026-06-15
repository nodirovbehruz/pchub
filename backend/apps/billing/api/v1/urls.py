from django.urls import path

from .views.dashboard import DashboardStatsAPIView
from .views.analytics import (
    AnalyticsOverviewAPIView,
    AnalyticsVisitorsAPIView,
    AnalyticsShiftsAPIView,
    AnalyticsClientsAPIView,
    AnalyticsEquipmentAPIView,
    AnalyticsSalesAPIView,
    AnalyticsGamesAPIView,
    AnalyticsTransfersAPIView,
)
from .views.extra import CashOrderListCreateAPIView, OperationLogListAPIView
from .views.shifts import ShiftCurrentAPIView, ShiftOpenAPIView, ShiftCloseAPIView
from .views.billing import (
    AdminDashboardStatsAPIView,
    ClientBuyTariffAPIView,
    ClientTariffsAPIView,
    ClosePostpaidAPIView,
    DeductMinuteAPIView,
    GuestPostpaidCloseAPIView,
    GuestPostpaidStartAPIView,
    GuestStatusAPIView,
    MyBalanceAPIView,
    MySessionAPIView,
    MyVisitsAPIView,
    PaymentListAPIView,
    PaymentRefundAPIView,
    StartPostpaidAPIView,
    TariffPlanCreateAPIView,
    TariffPlanDeleteAPIView,
    TariffPlanDetailAPIView,
    TariffPlanListAPIView,
    TopUpAPIView,
    UserClubProfilePatchAPIView,
    UserListWithBalanceAPIView,
)

urlpatterns = [
    # Admin endpoints
    path("admin/stats/", AdminDashboardStatsAPIView.as_view(), name="admin-stats"),
    path(
        "admin/users/", UserListWithBalanceAPIView.as_view(), name="users-balance-list"
    ),
    path("admin/topup/", TopUpAPIView.as_view(), name="topup"),
    path("admin/users/<int:user_id>/profile/", UserClubProfilePatchAPIView.as_view(), name="user-profile-patch"),
    path("admin/payments/", PaymentListAPIView.as_view(), name="payment-list"),
    path("admin/payments/<int:pk>/refund/", PaymentRefundAPIView.as_view(), name="payment-refund"),
    path("admin/postpaid/start/", StartPostpaidAPIView.as_view(), name="postpaid-start"),
    path("admin/postpaid/close/", ClosePostpaidAPIView.as_view(), name="postpaid-close"),
    # Guest (walk-in) postpaid on a PC
    path("admin/postpaid/guest/start/", GuestPostpaidStartAPIView.as_view(), name="guest-postpaid-start"),
    path("admin/postpaid/guest/close/", GuestPostpaidCloseAPIView.as_view(), name="guest-postpaid-close"),
    path("guest/status/", GuestStatusAPIView.as_view(), name="guest-status"),
    # Tariff plan endpoints (v2 — full CRUD with nested prices)
    path("tariffs/", TariffPlanListAPIView.as_view(), name="tariff-list"),
    path("tariffs/<int:pk>/", TariffPlanDetailAPIView.as_view(), name="tariff-detail"),
    # Legacy endpoints (kept for old frontend)
    path(
        "admin/tariffs/create/", TariffPlanCreateAPIView.as_view(), name="tariff-create"
    ),
    path(
        "admin/tariffs/<int:pk>/delete/",
        TariffPlanDeleteAPIView.as_view(),
        name="tariff-delete",
    ),
    # Cash orders (PKO / RKO)
    path("cash-orders/", CashOrderListCreateAPIView.as_view(), name="cash-order-list"),
    # Operation log
    path("logs/", OperationLogListAPIView.as_view(), name="operation-log-list"),
    # Shift management
    path("shifts/current/", ShiftCurrentAPIView.as_view(), name="shift-current"),
    path("shifts/open/", ShiftOpenAPIView.as_view(), name="shift-open"),
    path("shifts/close/", ShiftCloseAPIView.as_view(), name="shift-close"),
    # Dashboard
    path("dashboard/", DashboardStatsAPIView.as_view(), name="dashboard-stats"),
    # Analytics
    path("analytics/", AnalyticsOverviewAPIView.as_view(), name="analytics-overview"),
    path("analytics/visitors/", AnalyticsVisitorsAPIView.as_view(), name="analytics-visitors"),
    path("analytics/shifts/", AnalyticsShiftsAPIView.as_view(), name="analytics-shifts"),
    path("analytics/clients/", AnalyticsClientsAPIView.as_view(), name="analytics-clients"),
    path("analytics/equipment/", AnalyticsEquipmentAPIView.as_view(), name="analytics-equipment"),
    path("analytics/sales/", AnalyticsSalesAPIView.as_view(), name="analytics-sales"),
    path("analytics/games/", AnalyticsGamesAPIView.as_view(), name="analytics-games"),
    path("analytics/transfers/", AnalyticsTransfersAPIView.as_view(), name="analytics-transfers"),
    # Client endpoints (user identified by JWT — no hardware_id needed)
    path("balance/", MyBalanceAPIView.as_view(), name="my-balance"),
    path("deduct/", DeductMinuteAPIView.as_view(), name="deduct-minute"),
    path("my-session/", MySessionAPIView.as_view(), name="my-session"),
    path("my-visits/", MyVisitsAPIView.as_view(), name="my-visits"),
    path("client/tariffs/", ClientTariffsAPIView.as_view(), name="client-tariffs"),
    path("client/buy-tariff/", ClientBuyTariffAPIView.as_view(), name="client-buy-tariff"),
]
