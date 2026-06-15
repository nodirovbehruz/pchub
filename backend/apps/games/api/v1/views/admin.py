from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.permissions.admin import IsAdmin
from apps.games.services.implementation.session import GameSessionService


@extend_schema(tags=["Admin - Games"])
class GameStatisticsAPIView(APIView):
    """
    Admin-only endpoint: Get overall game statistics

    Returns aggregated statistics for all games including:
    - Total hours played
    - Total sessions
    - Unique players
    - Currently playing count
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    service = GameSessionService()

    def get(self, request):
        result = self.service.get_game_statistics()
        return Response(result)


@extend_schema(tags=["Admin - Sessions"])
class ActiveSessionsAPIView(APIView):
    """
    Admin-only endpoint: Get all active gaming sessions

    Returns list of all currently active sessions with:
    - User information
    - Computer information
    - Game being played
    - Session duration
    """

    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    service = GameSessionService()

    def get(self, request):
        result = self.service.get_active_sessions()
        return Response(result)
