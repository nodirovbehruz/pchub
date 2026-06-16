from django.urls import path

from apps.clubs.api.v1.views import (
    ClubBrandingAPIView,
    ClubBrandingUploadAPIView,
    ClubDadataLookupAPIView,
    ClubRetrieveUpdateAPIView,
    ClubSettingsAPIView,
    ClubSubscriptionAPIView,
    ClubTelegramTestAPIView,
    ClubTokenRegenerateAPIView,
    ClubTokenVerifyAPIView,
    ClubPromisedPaymentAPIView,
    MyClubsListView,
)
from apps.clubs.api.v1.client_views import (
    ClientGroupListCreateAPIView,
    ClientGroupDetailAPIView,
    ClientAssignGroupAPIView,
    ClientCommentListCreateAPIView,
    ClientCommentDetailAPIView,
)
from apps.clubs.api.v1.billing_views import (
    SubscriptionPlansAPIView,
    ClubWalletAPIView,
    ClubWalletTopupAPIView,
    ClubBuyPlanAPIView,
    ClubGrantSubscriptionAPIView,
)

app_name = "clubs"

urlpatterns = [
    path("my/", MyClubsListView.as_view(), name="my-clubs"),
    path("verify-token/", ClubTokenVerifyAPIView.as_view(), name="club-verify-token"),
    # Client groups + comments
    path("client-groups/", ClientGroupListCreateAPIView.as_view(), name="client-group-list"),
    path("client-groups/<int:pk>/", ClientGroupDetailAPIView.as_view(), name="client-group-detail"),
    # CustomUser PK is a UUID — `<int:user_id>` never matched (404 in prod).
    path("clients/<uuid:user_id>/group/", ClientAssignGroupAPIView.as_view(), name="client-assign-group"),
    path("clients/<uuid:user_id>/comments/", ClientCommentListCreateAPIView.as_view(), name="client-comments"),
    path("client-comments/<int:pk>/", ClientCommentDetailAPIView.as_view(), name="client-comment-detail"),
    path("<int:pk>/", ClubRetrieveUpdateAPIView.as_view(), name="club-detail"),
    path("<int:pk>/regenerate-token/", ClubTokenRegenerateAPIView.as_view(), name="club-regenerate-token"),
    path("<int:pk>/settings/", ClubSettingsAPIView.as_view(), name="club-settings"),
    path("<int:pk>/branding/", ClubBrandingAPIView.as_view(), name="club-branding"),
    path("<int:pk>/settings/branding/", ClubBrandingUploadAPIView.as_view(), name="club-branding-upload"),
    path("<int:pk>/telegram/test/", ClubTelegramTestAPIView.as_view(), name="club-telegram-test"),
    path("<int:pk>/dadata/party/", ClubDadataLookupAPIView.as_view(), name="club-dadata-party"),
    path("<int:pk>/subscription/", ClubSubscriptionAPIView.as_view(), name="club-subscription"),
    path("<int:pk>/promised-payment/", ClubPromisedPaymentAPIView.as_view(), name="club-promised-payment"),
    # ── B2B billing: wallet + subscription purchase ──
    path("plans/", SubscriptionPlansAPIView.as_view(), name="subscription-plans"),
    path("<int:pk>/wallet/", ClubWalletAPIView.as_view(), name="club-wallet"),
    path("<int:pk>/wallet/topup/", ClubWalletTopupAPIView.as_view(), name="club-wallet-topup"),
    path("<int:pk>/subscription/buy/", ClubBuyPlanAPIView.as_view(), name="club-subscription-buy"),
    path("<int:pk>/subscription/grant/", ClubGrantSubscriptionAPIView.as_view(), name="club-subscription-grant"),
]
