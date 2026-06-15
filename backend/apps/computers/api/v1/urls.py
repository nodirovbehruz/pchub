from django.urls import include, path

from apps.computers.api.v1.views.admin import ComputersStatusAPIView
from apps.computers.api.v1.views.chat import (
    AdminChatThreadsAPIView,
    AdminChatMessagesAPIView,
)
from apps.computers.api.v1.views.session import (
    AdminNotifyAPIView,
    AdminSessionFineAPIView,
    AdminSessionStartAPIView,
    AdminSessionStopAPIView,
    AdminSessionTransferAPIView,
)
from apps.computers.api.v1.views.command import (
    AdminCommandCancelAPIView,
    AdminCommandListCreateAPIView,
    BulkCommandAPIView,
    CommandStatusUpdateAPIView,
    PendingCommandsAPIView,
)
from apps.computers.api.v1.views.computer import (
    ComputerDetailAPIView,
    ComputerHeartbeatAPIView,
    ComputerHighAccessAPIView,
    ComputerListAPIView,
    ComputerPositionUpdateAPIView,
    ComputerRegistrationAPIView,
    ComputerUpdateSpecsAPIView,
)
from apps.computers.api.v1.views.computer_game import (
    InstalledGameAddAPIView,
    InstalledGameRemoveAPIView,
    InstalledGamesListAPIView,
    InstalledGamesSyncAPIView,
    InstalledGameUpdateAPIView,
)
from apps.computers.api.v1.views.group import (
    ComputerGroupDetailAPIView,
    ComputerGroupListCreateAPIView,
)
from apps.computers.api.v1.views.metrics import (
    ComputerMetricsCreateAPIView,
    ComputerMetricsHistoryAPIView,
)

app_name = "computers"

# Computer endpoints
computer_urlpatterns = [
    path("register/", ComputerRegistrationAPIView.as_view(), name="computer-register"),
    path("", ComputerListAPIView.as_view(), name="computer-list"),
    path("<int:computer_id>/", ComputerDetailAPIView.as_view(), name="computer-detail"),
    path(
        "<int:computer_id>/specs/",
        ComputerUpdateSpecsAPIView.as_view(),
        name="computer-update-specs",
    ),
    path(
        "<int:computer_id>/heartbeat/",
        ComputerHeartbeatAPIView.as_view(),
        name="computer-heartbeat",
    ),
    path(
        "<int:computer_id>/position/",
        ComputerPositionUpdateAPIView.as_view(),
        name="computer-position",
    ),
    path(
        "<int:pk>/high-access/",
        ComputerHighAccessAPIView.as_view(),
        name="computer-high-access",
    ),
]

# Admin endpoints
admin_urlpatterns = [
    path("status/", ComputersStatusAPIView.as_view(), name="computers-status"),
]

# Software management command endpoints (admin)
admin_command_urlpatterns = [
    path("", AdminCommandListCreateAPIView.as_view(), name="admin-commands"),
    path("bulk/", BulkCommandAPIView.as_view(), name="bulk-commands"),
    path(
        "<int:command_id>/cancel/",
        AdminCommandCancelAPIView.as_view(),
        name="admin-command-cancel",
    ),
]

# Software management command endpoints (PC client)
command_urlpatterns = [
    path("pending/", PendingCommandsAPIView.as_view(), name="commands-pending"),
    path(
        "<int:command_id>/status/",
        CommandStatusUpdateAPIView.as_view(),
        name="command-status-update",
    ),
]

# Metrics endpoints (for C# app integration)
metrics_urlpatterns = [
    path("", ComputerMetricsCreateAPIView.as_view(), name="metrics-create"),
    path(
        "<int:computer_id>/history/",
        ComputerMetricsHistoryAPIView.as_view(),
        name="metrics-history",
    ),
]

# Computer groups (club zones)
group_urlpatterns = [
    path("", ComputerGroupListCreateAPIView.as_view(), name="group-list-create"),
    path(
        "<int:group_id>/",
        ComputerGroupDetailAPIView.as_view(),
        name="group-detail",
    ),
]

# Installed games endpoints (for C# app integration)
installed_games_urlpatterns = [
    path("add/", InstalledGameAddAPIView.as_view(), name="installed-game-add"),
    path("remove/", InstalledGameRemoveAPIView.as_view(), name="installed-game-remove"),
    path("sync/", InstalledGamesSyncAPIView.as_view(), name="installed-games-sync"),
    path(
        "<int:computer_id>/",
        InstalledGamesListAPIView.as_view(),
        name="installed-games-list",
    ),
    path(
        "<int:computer_id>/<int:steam_app_id>/",
        InstalledGameUpdateAPIView.as_view(),
        name="installed-game-update",
    ),
]

urlpatterns = [
    path("", include((computer_urlpatterns, app_name))),
    path("groups/", include((group_urlpatterns, app_name))),
    path("metrics/", include((metrics_urlpatterns, app_name))),
    path("installed-games/", include((installed_games_urlpatterns, app_name))),
    path("admin/computers/", include((admin_urlpatterns, app_name))),
    path("admin/commands/", include((admin_command_urlpatterns, app_name))),
    path("commands/", include((command_urlpatterns, app_name))),
    path("admin/session/start/", AdminSessionStartAPIView.as_view(), name="session-start"),
    path("admin/session/stop/", AdminSessionStopAPIView.as_view(), name="session-stop"),
    path("admin/session/transfer/", AdminSessionTransferAPIView.as_view(), name="session-transfer"),
    path("admin/session/fine/", AdminSessionFineAPIView.as_view(), name="session-fine"),
    path("admin/notify/", AdminNotifyAPIView.as_view(), name="admin-notify"),
    path("admin/chat/", AdminChatThreadsAPIView.as_view(), name="admin-chat-threads"),
    path("admin/chat/<int:computer_id>/", AdminChatMessagesAPIView.as_view(), name="admin-chat-messages"),
]
