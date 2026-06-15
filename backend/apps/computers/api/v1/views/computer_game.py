from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.permissions.admin import IsAdmin
from apps.computers.api.v1.serializers.computer_game import (
    ComputerGameCreateSerializer,
    ComputerGameSerializer,
    ComputerGameUpdateSerializer,
    InstalledGamesListSerializer,
)
from apps.computers.repositories.implementation.computer import ComputerRepository
from apps.computers.repositories.implementation.computer_game import (
    ComputerGameRepository,
)
from apps.computers.services.implementation.computer_game import ComputerGameService
from apps.games.repositories.implementation.game import GameRepository


@extend_schema(tags=["Computers - Installed Games"])
class InstalledGameAddAPIView(generics.CreateAPIView):
    """
    Add or update an installed game on a computer from C# app

    Automatically creates the game if it doesn't exist.
    Updates installation info if game is already tracked.

    Example C# request:
    ```json
    {
        "computer_id": 1,
        "steam_app_id": 730,
        "game_name": "Counter-Strike: Global Offensive",
        "install_path": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Counter-Strike Global Offensive",
        "install_size_gb": 25.5
    }
    ```
    """

    serializer_class = ComputerGameCreateSerializer
    permission_classes = [IsAdmin]
    service = ComputerGameService(
        computer_game_repository=ComputerGameRepository(),
        computer_repository=ComputerRepository(),
        game_repository=GameRepository(),
    )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Add installed game
        computer_game = self.service.add_installed_game(
            computer_id=serializer.validated_data["computer_id"],
            steam_app_id=serializer.validated_data["steam_app_id"],
            game_name=serializer.validated_data.get("game_name"),
            install_path=serializer.validated_data.get("install_path"),
            install_size_gb=serializer.validated_data.get("install_size_gb"),
        )

        # Return response
        response_serializer = ComputerGameSerializer(
            computer_game, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Computers - Installed Games"])
class InstalledGameRemoveAPIView(generics.CreateAPIView):
    """
    Mark a game as uninstalled on a computer

    Called from C# app when a game is uninstalled.
    """

    serializer_class = ComputerGameCreateSerializer
    permission_classes = [IsAdmin]
    service = ComputerGameService()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Remove installed game
        computer_game = self.service.remove_installed_game(
            computer_id=serializer.validated_data["computer_id"],
            steam_app_id=serializer.validated_data["steam_app_id"],
        )

        # Return response
        response_serializer = ComputerGameSerializer(
            computer_game, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@extend_schema(tags=["Computers - Installed Games"])
class InstalledGamesListAPIView(APIView):
    """
    Get list of all installed games for a computer with user statistics

    Query parameters:
    - installed_only: true/false (default: true)

    Returns games with user's play time and statistics
    """

    permission_classes = [permissions.IsAuthenticated]
    service = ComputerGameService()

    def get(self, request, computer_id):
        installed_only = (
            request.query_params.get("installed_only", "true").lower() == "true"
        )

        # Get installed games with user stats from service
        data = self.service.get_installed_games_with_user_stats(
            computer_id=computer_id,
            user=request.user,
            installed_only=installed_only,
        )

        # Serialize games
        games_list = []
        for game_data in data["games_with_stats"]:
            serialized = ComputerGameSerializer(
                game_data["computer_game"], context={"request": request}
            ).data
            serialized["user_total_hours"] = game_data["user_total_hours"]
            serialized["user_last_played"] = game_data["user_last_played"]
            serialized["user_total_sessions"] = game_data["user_total_sessions"]
            games_list.append(serialized)

        return Response(
            {
                "computer_id": data["computer_id"],
                "computer_name": data["computer_name"],
                "total_games": data["total_games"],
                "total_size_gb": data["total_size_gb"],
                "installed_games": games_list,
            }
        )


@extend_schema(tags=["Computers - Installed Games"])
class InstalledGamesSyncAPIView(generics.CreateAPIView):
    """
    Sync installed games list from C# app (bulk update)

    Useful for syncing all installed games at once when the C# app starts.

    Example C# request:
    ```json
    {
        "computer_id": 1,
        "games": [
            {
                "steam_app_id": 730,
                "game_name": "Counter-Strike: Global Offensive",
                "install_path": "C:\\...",
                "install_size_gb": 25.5
            },
            {
                "steam_app_id": 440,
                "game_name": "Team Fortress 2",
                "install_size_gb": 15.2
            }
        ]
    }
    ```
    """

    serializer_class = InstalledGamesListSerializer
    permission_classes = [IsAdmin]
    service = ComputerGameService()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Sync games
        result = self.service.sync_installed_games(
            computer_id=serializer.validated_data["computer_id"],
            games_list=serializer.validated_data["games"],
        )

        # Serialize added/updated games
        added_serializer = ComputerGameSerializer(result["added_games"], many=True)
        updated_serializer = ComputerGameSerializer(result["updated_games"], many=True)

        return Response(
            {
                "computer_id": result["computer_id"],
                "summary": {
                    "added_count": result["added_count"],
                    "updated_count": result["updated_count"],
                    "error_count": result["error_count"],
                },
                "added_games": added_serializer.data,
                "updated_games": updated_serializer.data,
                "errors": result["errors"],
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["Computers - Installed Games"])
class InstalledGameUpdateAPIView(generics.UpdateAPIView):
    """
    Update game installation details

    PATCH endpoint to update install path or size
    """

    serializer_class = ComputerGameUpdateSerializer
    permission_classes = [IsAdmin]
    service = ComputerGameService()

    def update(self, request, computer_id, steam_app_id):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Update game info
        computer_game = self.service.update_game_install_info(
            computer_id=computer_id,
            steam_app_id=steam_app_id,
            install_path=serializer.validated_data.get("install_path"),
            install_size_gb=serializer.validated_data.get("install_size_gb"),
        )

        # Return response
        response_serializer = ComputerGameSerializer(
            computer_game, context={"request": request}
        )
        return Response(response_serializer.data)
