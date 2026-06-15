from django.db.models import Count, Q, Sum
from django.utils.text import slugify
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.computers.models import Computer, ComputerGame
from apps.games.api.v1.serializers.game import GameSerializer
from apps.games.models import Game, GameSession, GamePlatform, SessionStatus
from apps.games.services.implementation.session import GameSessionService


@extend_schema(tags=["Games - Dashboard"])
class UserStatisticsAPIView(APIView):
    """
    User statistics dashboard

    Returns user's statistics:
    - User info (id, username, email)
    - Total hours played across all games
    - Total number of games played
    - Top 3 most played games
    - Total orders count
    - Order history (last 10 orders)
    """

    permission_classes = [permissions.IsAuthenticated]
    service = GameSessionService()

    def get(self, request):
        data = self.service.get_user_statistics(request.user)
        return Response(data)


# Schemas for ComputerGamesListAPIView
class _ComputerInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="Computer database ID")
    name = serializers.CharField(help_text="Computer name")
    hardware_id = serializers.CharField(help_text="Computer hardware ID")


class _ComputerGamesListResponseSerializer(serializers.Serializer):
    computer = _ComputerInfoSerializer()
    games = GameSerializer(many=True)
    total_games = serializers.IntegerField()


@extend_schema(
    tags=["Games - Dashboard"],
    summary="List games on a specific computer",
    description="""
    Retrieves a list of all games installed on a specific computer,
    identified by either its database ID or hardware ID.
    This is primarily used by the C# desktop application.
    """,
    parameters=[
        OpenApiParameter(
            name="computer_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="The database ID of the computer.",
        ),
        OpenApiParameter(
            name="hardware_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="The unique hardware ID of the computer.",
        ),
    ],
    responses={
        200: _ComputerGamesListResponseSerializer,
        400: OpenApiResponse(
            description="Bad Request - computer_id or hardware_id is required"
        ),
        404: OpenApiResponse(description="Computer not found"),
    },
)
class ComputerGamesListAPIView(APIView):
    """
    Get list of games available on a specific computer

    Returns all games installed on the specified computer.
    Used by C# app to show game selection menu.

    Query Parameters:
    - computer_id: ID of the computer

    OR use hardware_id:
    - hardware_id: Hardware ID of the computer
    """

    permission_classes = [permissions.IsAuthenticated]
    service = GameSessionService()

    def get(self, request):
        computer_id = request.query_params.get("computer_id")
        hardware_id = request.query_params.get("hardware_id")

        # Get data from service
        data = self.service.get_computer_games(
            computer_id=int(computer_id) if computer_id else None,
            hardware_id=hardware_id,
            user=request.user,
        )

        # Serialize games
        games_data = []
        for game_info in data["games"]:
            game_dict = GameSerializer(
                game_info["game"], context={"request": request}
            ).data
            game_dict["hours_played"] = game_info["hours_played"]
            game_dict["last_played"] = game_info["last_played"]
            games_data.append(game_dict)

        computer = data["computer"]
        return Response(
            {
                "computer": {
                    "id": computer.id,
                    "name": computer.name,
                    "hardware_id": computer.hardware_id,
                },
                "games": games_data,
                "total_games": data["total_games"],
            }
        )


@extend_schema(tags=["Games - Dashboard"])
class DashboardAPIView(APIView):
    """
    Full dashboard for the C# desktop client.

    Returns:
    - user info
    - statistics (hours, games, sessions)
    - most_played_games (top 5)
    - recent_sessions (last 5)
    - active_session (current session if any)
    - popular_games (top 5 by total play hours across all users)
    - leaderboard (top 10 users by hours)
    """

    permission_classes = [permissions.IsAuthenticated]
    service = GameSessionService()

    def get(self, request):
        user = request.user
        data = self.service.get_account_sessions(user)
        sessions_qs = data["sessions"]
        statistics = data["statistics"]

        def _icon_url(game, req):
            """Return icon (small/square) URL for a game."""
            if game.icon:
                return req.build_absolute_uri(game.icon.url)
            if game.app_id:
                return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{game.app_id}/capsule_sm_120.jpg"
            return None

        def _header_url(game, req):
            """Return header/banner image URL for a game."""
            if game.header_image:
                return req.build_absolute_uri(game.header_image.url)
            if game.app_id:
                return f"https://cdn.cloudflare.steamstatic.com/steam/apps/{game.app_id}/header.jpg"
            return None

        def _text_image_url(game, req):
            """Return stylized text/logo image URL for a game."""
            if game.text_image:
                return req.build_absolute_uri(game.text_image.url)
            return None

        def _game_image(game, req):
            """Legacy: best available image (header preferred)."""
            return _header_url(game, req) or _icon_url(game, req)

        def _random_game_entry():
            """Return a random active game formatted as a session-like entry (fallback)."""
            game = Game.objects.filter(is_active=True).order_by("?").first()
            if not game:
                return None
            return {
                "game_id": game.id,
                "game_name": game.name,
                "platform": game.platform,
                "executable_path": game.executable_path,
                "app_id": game.app_id,
                "hours_played": 0.0,
                "last_played": None,
                "icon_url": _icon_url(game, request),
                "header_image_url": _header_url(game, request),
                "text_image_url": _text_image_url(game, request),
            }

        # Most played games for this user
        most_played = sessions_qs.select_related("game").order_by(
            "-total_hours_played"
        )[:5]
        most_played_games = [
            {
                "game_id": s.game.id,
                "game_name": s.game.name,
                "platform": s.game.platform,
                "executable_path": s.game.executable_path,
                "app_id": s.game.app_id,
                "hours_played": float(s.total_hours_played),
                "last_played": s.last_played,
                "icon_url": _icon_url(s.game, request),
                "header_image_url": _header_url(s.game, request),
                "text_image_url": _text_image_url(s.game, request),
            }
            for s in most_played
        ]
        # No fake fallback: a user who hasn't played anything shows an empty state,
        # not random club games (which read as "non-existent data" the user never played).

        # Recent sessions
        recent = sessions_qs.select_related("game").order_by("-last_played")[:5]
        recent_sessions = [
            {
                "game_id": s.game.id,
                "game_name": s.game.name,
                "platform": s.game.platform,
                "executable_path": s.game.executable_path,
                "app_id": s.game.app_id,
                "hours_played": float(s.total_hours_played),
                "last_played": s.last_played,
                "icon_url": _icon_url(s.game, request),
                "header_image_url": _header_url(s.game, request),
                "text_image_url": _text_image_url(s.game, request),
            }
            for s in recent
        ]
        # No fake fallback — empty "Continue playing" stays empty for a fresh user.

        # Active session (if any)
        active_qs = (
            sessions_qs.filter(session_status=SessionStatus.ACTIVE)
            .select_related("game")
            .first()
        )
        active_session = None
        if active_qs:
            active_session = {
                "game_id": active_qs.game.id,
                "game_name": active_qs.game.name,
                "platform": active_qs.game.platform,
                "executable_path": active_qs.game.executable_path,
                "app_id": active_qs.game.app_id,
                "hours_played": float(active_qs.total_hours_played),
                "last_played": active_qs.last_played,
                "icon_url": _icon_url(active_qs.game, request),
                "header_image_url": _header_url(active_qs.game, request),
                "text_image_url": _text_image_url(active_qs.game, request),
            }

        # Popular games (all users, ranked by total hours)
        popular_qs = Game.objects.annotate(
            total_hours=Sum("sessions__total_hours_played")
        ).order_by("-total_hours")[:5]
        popular_games = [
            {
                "id": g.id,
                "name": g.name,
                "platform": g.platform,
                "executable_path": g.executable_path,
                "app_id": g.app_id,
                "total_hours": float(g.total_hours or 0),
                "icon_url": _icon_url(g, request),
                "header_image_url": _header_url(g, request),
                "text_image_url": _text_image_url(g, request),
            }
            for g in popular_qs
        ]

        # Leaderboard (top 10 users by total hours)
        from django.contrib.auth import get_user_model

        User = get_user_model()
        leaderboard_qs = (
            GameSession.objects.values("account__username")
            .annotate(
                total_hours=Sum("total_hours_played"),
                games_played=Count("game", distinct=True),
            )
            .order_by("-total_hours")[:10]
        )
        leaderboard = [
            {
                "rank": i + 1,
                "username": row["account__username"],
                "total_hours": float(row["total_hours"] or 0),
                "games_played": row["games_played"],
            }
            for i, row in enumerate(leaderboard_qs)
        ]

        return Response(
            {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                },
                "statistics": {
                    "total_hours_played": statistics["total_hours_played"],
                    "total_games": statistics["total_games"],
                    "total_sessions": sessions_qs.count(),
                },
                "most_played_games": most_played_games,
                "recent_sessions": recent_sessions,
                "active_session": active_session,
                "popular_games": popular_games,
                "leaderboard": leaderboard,
            }
        )


@extend_schema(tags=["Games - Local"])
class ComputerGameLinkAPIView(APIView):
    """C# shell: link an EXISTING catalog game to this PC by game_id (the shell
    already matched it). Was POSTing to a non-existent route → 404 silently
    swallowed, so catalog games never linked. AllowAny like other PC self-reports
    (keyed by computer_id + game_id)."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from apps.computers.models import Computer
        from apps.computers.models.computer_game import ComputerGame
        cid = request.data.get("computer_id")
        gid = request.data.get("game_id")
        if not cid or not gid:
            return Response({"error": "computer_id и game_id обязательны"}, status=status.HTTP_400_BAD_REQUEST)
        if not Computer.objects.filter(id=cid).exists():
            return Response({"error": "ПК не найден"}, status=status.HTTP_404_NOT_FOUND)
        if not Game.objects.filter(id=gid).exists():
            return Response({"error": "Игра не найдена"}, status=status.HTTP_404_NOT_FOUND)
        size = request.data.get("install_size_gb")
        cg, created = ComputerGame.objects.update_or_create(
            computer_id=cid, game_id=gid,
            defaults={
                "is_installed": True,
                "install_path": request.data.get("install_path") or "",
                "install_size_gb": size if size not in ("", None) else None,
            },
        )
        return Response({"success": True, "created": created, "computer_game_id": cg.id},
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class AddLocalGameAPIView(APIView):
    """
    Client app: register a local (non-Steam) game and add it to this computer.

    Creates the Game record if it doesn't exist, then links it to the computer.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        name = request.data.get("name", "").strip()
        executable_path = request.data.get("executable_path", "").strip()
        computer_id = request.data.get("computer_id")

        if not name:
            return Response(
                {"error": "name is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not executable_path:
            return Response(
                {"error": "executable_path is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not computer_id:
            return Response(
                {"error": "computer_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            computer = Computer.objects.get(pk=computer_id)
        except Computer.DoesNotExist:
            return Response(
                {"error": "Computer not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Try to find existing game by name (case-insensitive)
        # This prevents duplicate Game records when the same game is found on different PCs at different paths
        game = Game.objects.filter(name__iexact=name).first()
        
        if not game:
            import hashlib
            import uuid
            from django.db import IntegrityError, transaction

            # Build a unique slug using md5 to ensure consistency
            base_slug = slugify(name)[:200]
            path_hash = hashlib.md5(executable_path.encode('utf-8')).hexdigest()[:6]
            slug = f"{base_slug}-{path_hash}" if base_slug else f"local-{path_hash}"

            try:
                with transaction.atomic():
                    game = Game.objects.create(
                        platform=GamePlatform.LOCAL,
                        executable_path=executable_path,
                        name=name,
                        slug=slug,
                    )
                created = True
            except IntegrityError:
                # Race condition: game was created concurrently, or slug collided
                game = Game.objects.filter(name__iexact=name).first()
                if not game:
                    # Still not found? Slug collision. Generate a unique fallback slug
                    fallback_slug = f"{slug}-{uuid.uuid4().hex[:6]}"
                    with transaction.atomic():
                        game = Game.objects.create(
                            platform=GamePlatform.LOCAL,
                            executable_path=executable_path,
                            name=name,
                            slug=fallback_slug,
                        )
                created = False
        else:
            created = False
            # If it's a local game and has no executable path set, update it
            if game.platform == GamePlatform.LOCAL and not game.executable_path:
                game.executable_path = executable_path
                game.save(update_fields=["executable_path"])
        # Update name if it changed
        if game.name != name:
            game.name = name
            game.save(update_fields=["name"])

        # Handle icon / images if provided
        if "icon" in request.FILES:
            game.icon = request.FILES["icon"]
        if "header_image" in request.FILES:
            game.header_image = request.FILES["header_image"]
        
        if "icon" in request.FILES or "header_image" in request.FILES:
            game.save()

        ComputerGame.objects.get_or_create(
            computer=computer,
            game=game,
            defaults={"is_installed": True, "install_path": executable_path},
        )

        return Response(
            {"id": game.id, "name": game.name, "platform": game.platform, "icon_url": game.icon.url if game.icon else None},
            status=status.HTTP_201_CREATED,
        )
