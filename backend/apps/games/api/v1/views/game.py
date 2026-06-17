from django.db.models import Count, Sum
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, generics, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.games.api.v1.serializers.game import (
    GameBulkImportSerializer,
    GameCreateSerializer,
    GameDetailSerializer,
    GameListSerializer,
    GameUpdateSerializer,
)
from apps.games.models import Game
from apps.games.repositories.implementation.game import GameRepository
from apps.games.services.implementation.game import (
    GameCreateService,
    GameDeleteService,
    GameDetailService,
    GameListService,
    GameUpdateService,
)


class IsAdminOrReadOnly(BasePermission):
    """Allow read-only for authenticated users, write only for admins"""

    def has_permission(self, request, view):
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return request.user and request.user.is_authenticated
        # Admin write access. user_type is stored LOWERCASE ('admin') — comparing to
        # "ADMIN" never matched, so all game writes 403'd even for platform admins.
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin":
            return True
        # Club owners/managers may also manage the catalog (they reach this page).
        from apps.clubs.models import Club, ClubMembership
        club_id = getattr(request, "current_club_id", None)
        if club_id:
            return Club.objects.filter(id=club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
        return Club.objects.filter(owner=u).exists() or ClubMembership.objects.filter(
            user=u, is_active=True, role__in=["owner", "manager"]
        ).exists()


class IsPlatformAdminOrReadOnly(BasePermission):
    """Read for any authenticated user; WRITE only for the platform admin. The Game
    catalog is GLOBAL (no club FK) — letting a club owner/manager edit/delete/version-
    bump a game broke it for EVERY other club (fleet-wide auto-update, hidden/renamed
    games). Catalog mutations must be platform-admin-only."""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"


# ---------------------
# User-Facing Endpoints
# ---------------------


@extend_schema(
    tags=["Games - Library"],
    description="List all active games with pagination, search, and filtering",
    parameters=[
        OpenApiParameter(
            name="search",
            description="Search games by name, developer, or publisher",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="developer",
            description="Filter by developer",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="publisher",
            description="Filter by publisher",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="release_date__gte",
            description="Filter games released after this date (YYYY-MM-DD)",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="release_date__lte",
            description="Filter games released before this date (YYYY-MM-DD)",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="ordering",
            description="Sort by: name, -name, release_date, -release_date, total_players, -total_players, total_hours, -total_hours",
            required=False,
            type=str,
        ),
    ],
)
class GameListAPIView(generics.ListAPIView):
    """List all active games"""

    queryset = Game.objects.filter(is_active=True)
    serializer_class = GameListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    # Search configuration
    search_fields = ["name", "developer", "publisher"]

    # Ordering configuration
    ordering_fields = ["name", "release_date", "created_at"]
    ordering = ["name"]  # Default ordering

    # Filter configuration
    filterset_fields = {
        "developer": ["exact", "icontains"],
        "publisher": ["exact", "icontains"],
        "release_date": ["gte", "lte", "exact"],
    }

    service = GameListService(repository=GameRepository())

    def get_queryset(self):
        """
        Override to include computed properties for sorting
        """
        # Admin passes ?all=1 to see/re-enable INACTIVE games (a disabled game otherwise
        # vanished from the Apps panel forever). Default stays active-only for the shell.
        include_all = self.request.query_params.get("all") in ("1", "true", "yes")
        queryset = Game.objects.all() if include_all else self.service.execute(is_active=True)

        # Annotate for sorting by statistics
        queryset = queryset.annotate(
            total_players_count=Count("sessions__account", distinct=True),
            total_hours=Sum("sessions__total_hours_played"),
        )

        # Handle ordering by computed fields
        ordering = self.request.query_params.get("ordering", "")
        if "total_players" in ordering:
            queryset = queryset.order_by(
                "-total_players_count"
                if ordering.startswith("-")
                else "total_players_count"
            )
        elif "total_hours" in ordering:
            queryset = queryset.order_by(
                "-total_hours" if ordering.startswith("-") else "total_hours"
            )

        return queryset


@extend_schema(
    tags=["Games - Library"],
    description="Get detailed information about a specific game",
)
class GameDetailAPIView(generics.RetrieveAPIView):
    """Get game details by slug"""

    queryset = Game.objects.filter(is_active=True)
    serializer_class = GameDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"

    service = GameDetailService(repository=GameRepository())

    def get_object(self):
        """Get game using service"""
        slug = self.kwargs["slug"]
        return self.service.execute(slug=slug)


# ---------------------
# Admin Endpoints
# ---------------------


@extend_schema(tags=["Games - Admin"], description="Create a new game (Admin only)")
class GameCreateAPIView(generics.CreateAPIView):
    """Create new game (admin only)"""

    queryset = Game.objects.all()
    serializer_class = GameCreateSerializer
    permission_classes = [IsPlatformAdminOrReadOnly]

    service = GameCreateService(repository=GameRepository())

    def perform_create(self, serializer):
        """Create game using service"""
        data = serializer.validated_data
        return self.service.execute(data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game = self.perform_create(serializer)

        # Return detailed view
        response_serializer = GameDetailSerializer(game)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Games - Admin"], description="Update an existing game (Admin only)"
)
class GameUpdateAPIView(generics.UpdateAPIView):
    """Update game (admin only)"""

    queryset = Game.objects.all()
    serializer_class = GameUpdateSerializer
    permission_classes = [IsPlatformAdminOrReadOnly]
    lookup_field = "slug"

    service = GameUpdateService(repository=GameRepository())

    def perform_update(self, serializer):
        """Update game using service"""
        slug = self.kwargs["slug"]
        data = serializer.validated_data
        return self.service.execute(slug, data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        serializer = self.get_serializer(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        game = self.perform_update(serializer)

        # Return detailed view
        response_serializer = GameDetailSerializer(game)
        return Response(response_serializer.data)


@extend_schema(tags=["Games - Admin"], description="Release an update for a game.")
class GameReleaseUpdateAPIView(generics.GenericAPIView):
    """POST /api/v1/games/admin/games/<slug>/release-update/

    One-click «Выпустить обновление»: auto-stamps a fresh version on the game (no
    need to type a number) and immediately queues an `update` command for every
    online, idle PC that has this game on an older version. Busy PCs pick it up
    later via the background task. Returns { version, queued }."""

    queryset = Game.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"

    def post(self, request, slug):
        from django.utils import timezone
        from apps.computers.models import ComputerCommand
        from apps.computers.models.command import CommandStatus, CommandType
        from apps.computers.models.computer_game import ComputerGame
        from apps.games.tasks.auto_update import _pc_in_session

        # SECURITY: games are a GLOBAL catalog with a single `version`. Bumping it
        # queues update commands fleet-wide (here + the background task), so only a
        # platform admin may release a catalog update — a club owner triggering this
        # would force re-downloads on OTHER clubs' PCs. Club owners update their own
        # PCs via the club-scoped bulk command ("→ на ПК → Обновить").
        if not (getattr(request.user, "is_admin", False)
                or getattr(request.user, "user_type", "") == "admin"):
            return Response(
                {"error": "Выпуск обновления игры доступен только администратору платформы. "
                          "Для своих ПК используйте «→ на ПК → Обновить»."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            game = Game.objects.get(slug=slug)
        except Game.DoesNotExist:
            return Response({"error": "Игра не найдена"}, status=status.HTTP_404_NOT_FOUND)

        # Fresh version stamp — operator never types a number.
        game.version = timezone.localtime().strftime("upd-%Y%m%d-%H%M")
        game.save(update_fields=["version"])

        queued = 0
        installs = (
            ComputerGame.objects.filter(game=game, is_installed=True)
            .exclude(installed_version=game.version)
            .select_related("computer")
        )
        for cg in installs:
            pc = cg.computer
            if (pc.status or "").lower() != "online" or _pc_in_session(pc):
                continue
            # Dedup against PENDING *and* IN_PROGRESS — same as the periodic auto-update
            # task: a command flips to IN_PROGRESS while a large game downloads, so a
            # PENDING-only check re-queued duplicates on repeated release clicks.
            if ComputerCommand.objects.filter(
                computer=pc, game=game, command_type=CommandType.UPDATE,
                status__in=[CommandStatus.PENDING, CommandStatus.IN_PROGRESS],
            ).exists():
                continue
            ComputerCommand.objects.create(
                computer=pc, game=game, command_type=CommandType.UPDATE,
                status=CommandStatus.PENDING,
                payload={
                    "game_name": game.name,
                    "platform": getattr(game, "platform", "") or "",
                    "app_id": getattr(game, "app_id", "") or "",
                    "version": game.version,
                    "installer_url": getattr(game, "executable_path", "") or "",
                },
            )
            queued += 1

        return Response({
            "success": True, "version": game.version, "queued": queued,
            "message": f"Обновление выпущено. Сейчас обновляется ПК: {queued}; занятые — в простое.",
        })


@extend_schema(
    tags=["Games - Admin"], description="Delete/deactivate a game (Admin only)"
)
class GameDeleteAPIView(generics.DestroyAPIView):
    """Delete (soft delete) game (admin only)"""

    queryset = Game.objects.all()
    permission_classes = [IsPlatformAdminOrReadOnly]
    lookup_field = "slug"

    service = GameDeleteService(repository=GameRepository())

    def perform_destroy(self, instance):
        """Soft delete game using service"""
        slug = self.kwargs["slug"]
        self.service.execute(slug)

    def destroy(self, request, *args, **kwargs):
        self.perform_destroy(None)
        return Response(
            {"message": "Game deactivated successfully"}, status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Games - Admin"], description="Bulk import multiple games (Admin only)"
)
class GameBulkImportAPIView(generics.CreateAPIView):
    """Bulk import games (admin only)"""

    serializer_class = GameBulkImportSerializer
    permission_classes = [IsPlatformAdminOrReadOnly]

    service = GameCreateService(repository=GameRepository())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        games_data = serializer.validated_data["games"]
        created_games = []
        errors = []

        for game_data in games_data:
            try:
                game = self.service.execute(game_data)
                created_games.append(game)
            except Exception as e:
                errors.append(
                    {"game": game_data.get("name", "Unknown"), "error": str(e)}
                )

        return Response(
            {
                "created": len(created_games),
                "failed": len(errors),
                "errors": errors,
                "games": GameListSerializer(created_games, many=True).data,
            },
            status=(
                status.HTTP_201_CREATED
                if created_games
                else status.HTTP_400_BAD_REQUEST
            ),
        )
