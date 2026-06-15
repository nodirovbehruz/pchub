from django.urls import include, path

from apps.games.api.v1.views.admin import ActiveSessionsAPIView, GameStatisticsAPIView
from apps.games.api.v1.views.dashboard import (
    AddLocalGameAPIView,
    ComputerGameLinkAPIView,
    ComputerGamesListAPIView,
    DashboardAPIView,
    UserStatisticsAPIView,
)
from apps.games.api.v1.views.game import (
    GameBulkImportAPIView,
    GameCreateAPIView,
    GameDeleteAPIView,
    GameDetailAPIView,
    GameListAPIView,
    GameReleaseUpdateAPIView,
    GameUpdateAPIView,
)
from apps.games.api.v1.views.file_browser import FileBrowserAPIView
from apps.games.api.v1.views.category import (
    GameCategoryListCreateAPIView,
    GameCategoryDetailAPIView,
    GameCategoryReorderAPIView,
)
from apps.games.api.v1.views.session import (
    GameSessionEndAPIView,
    GameSessionListAPIView,
    GameSessionStartAPIView,
    GameSessionUpdateAPIView,
)

app_name = "games"

# Game library endpoints (user-facing)
game_urlpatterns = [
    path("", GameListAPIView.as_view(), name="game-list"),
    path("<slug:slug>/", GameDetailAPIView.as_view(), name="game-detail"),
]

# Admin game management endpoints
game_admin_urlpatterns = [
    path("create/", GameCreateAPIView.as_view(), name="game-create"),
    path("<slug:slug>/update/", GameUpdateAPIView.as_view(), name="game-update"),
    path("<slug:slug>/delete/", GameDeleteAPIView.as_view(), name="game-delete"),
    path("<slug:slug>/release-update/", GameReleaseUpdateAPIView.as_view(), name="game-release-update"),
    path("bulk-import/", GameBulkImportAPIView.as_view(), name="game-bulk-import"),
]

# Game session endpoints (for C# app integration)
session_urlpatterns = [
    path("update/", GameSessionUpdateAPIView.as_view(), name="session-update"),
    path("start/", GameSessionStartAPIView.as_view(), name="session-start"),
    path("end/", GameSessionEndAPIView.as_view(), name="session-end"),
    path("", GameSessionListAPIView.as_view(), name="session-list"),
]

# Admin session endpoints
admin_urlpatterns = [
    path("statistics/", GameStatisticsAPIView.as_view(), name="game-statistics"),
    path("active-sessions/", ActiveSessionsAPIView.as_view(), name="active-sessions"),
]

urlpatterns = [
    path("categories/", GameCategoryListCreateAPIView.as_view(), name="category-list"),
    path("categories/reorder/", GameCategoryReorderAPIView.as_view(), name="category-reorder"),
    path("categories/<int:pk>/", GameCategoryDetailAPIView.as_view(), name="category-detail"),
    path("games/", include((game_urlpatterns, app_name), namespace="game")),
    path(
        "admin/games/",
        include((game_admin_urlpatterns, app_name), namespace="game-admin"),
    ),
    path("sessions/", include((session_urlpatterns, app_name), namespace="session")),
    path("admin/sessions/", include((admin_urlpatterns, app_name), namespace="admin")),
    # User statistics and C# app integration endpoints
    path("my-stats/", UserStatisticsAPIView.as_view(), name="user-statistics"),
    path("computer/games/", ComputerGamesListAPIView.as_view(), name="computer-games"),
    path("computer/games/add/", ComputerGameLinkAPIView.as_view(), name="computer-game-link"),
    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),
    path("local/add/", AddLocalGameAPIView.as_view(), name="local-game-add"),
    path("browse-files/", FileBrowserAPIView.as_view(), name="file-browser"),
]
