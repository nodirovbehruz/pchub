from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.games.api.v1.serializers.session import (
    GameSessionEndSerializer,
    GameSessionSerializer,
    GameSessionStartSerializer,
    GameSessionUpdateSerializer,
)
from apps.games.repositories.implementation.game import GameRepository
from apps.games.repositories.implementation.session import GameSessionRepository
from apps.games.services.implementation.session import GameSessionService


@extend_schema(tags=["Games - Sessions"])
class GameSessionUpdateAPIView(generics.CreateAPIView):
    """
    Update game session hours from C# app

    POST endpoint for C# application to send hours played updates.
    Automatically creates game and session if they don't exist.
    """

    serializer_class = GameSessionUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    service = GameSessionService(
        session_repository=GameSessionRepository(), game_repository=GameRepository()
    )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update session hours
        session = self.service.update_session_hours(
            account=request.user,
            game_id=serializer.validated_data.get("game_id"),
            steam_app_id=serializer.validated_data.get("steam_app_id"),
            computer_id=serializer.validated_data["computer_id"],
            hours_to_add=serializer.validated_data["hours_to_add"],
            game_name=serializer.validated_data.get("game_name"),
        )

        # Return updated session
        response_serializer = GameSessionSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Games - Sessions"])
class GameSessionStartAPIView(generics.CreateAPIView):
    """
    Start a game session from C# app

    Called when user starts playing a game
    """

    serializer_class = GameSessionStartSerializer
    permission_classes = [permissions.IsAuthenticated]
    service = GameSessionService()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = self.service.start_session(
            account=request.user,
            game_id=serializer.validated_data.get("game_id"),
            steam_app_id=serializer.validated_data.get("steam_app_id"),
            computer_id=serializer.validated_data["computer_id"],
            game_name=serializer.validated_data.get("game_name"),
        )

        response_serializer = GameSessionSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Games - Sessions"])
class GameSessionEndAPIView(generics.CreateAPIView):
    """
    End a game session from C# app

    Called when user stops playing a game
    """

    serializer_class = GameSessionEndSerializer
    permission_classes = [permissions.IsAuthenticated]
    service = GameSessionService()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = self.service.end_session(
            account=request.user,
            game_id=serializer.validated_data.get("game_id"),
            steam_app_id=serializer.validated_data.get("steam_app_id"),
            computer_id=serializer.validated_data["computer_id"],
            hours_played=serializer.validated_data.get("hours_played"),
        )

        response_serializer = GameSessionSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Games - Sessions"])
class GameSessionListAPIView(generics.ListAPIView):
    """
    Get all game sessions for authenticated user

    Returns list of all games played with hours and statistics
    """

    serializer_class = GameSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    service = GameSessionService()

    def get_queryset(self):
        return self.service.get_account_sessions(self.request.user)["sessions"]

    def list(self, request, *args, **kwargs):
        # Get sessions and statistics
        data = self.service.get_account_sessions(request.user)

        # Serialize sessions
        serializer = self.get_serializer(data["sessions"], many=True)

        return Response({"sessions": serializer.data, "statistics": data["statistics"]})
