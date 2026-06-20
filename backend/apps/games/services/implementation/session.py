from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.games.models import Game, GameSession, SessionStatus
from apps.games.repositories.implementation.game import GameRepository
from apps.games.repositories.implementation.session import GameSessionRepository
from apps.games.repositories.interface.game import IGameRepository
from apps.games.repositories.interface.session import IGameSessionRepository
from apps.games.services.interface.session import IGameSessionService

User = get_user_model()


class GameSessionService(IGameSessionService):
    """Service for GameSession - handles C# app integration"""

    def __init__(
        self,
        session_repository: IGameSessionRepository = None,
        game_repository: IGameRepository = None,
    ):
        self.session_repository = session_repository or GameSessionRepository()
        self.game_repository = game_repository or GameRepository()

    def _resolve_game(self, game_id=None, steam_app_id=None, game_name=None) -> Game:
        """Resolve game by game_id (preferred) or steam_app_id fallback"""
        if game_id:
            game = self.game_repository.get_by_id(game_id)
            if not game:
                raise ValidationError({"game_id": "Game not found"})
            return game
        # Fallback: look up or create by steam_app_id (Steam games)
        name = game_name or f"Game {steam_app_id}"
        game, _ = self.game_repository.get_or_create_by_steam_id(
            steam_app_id=steam_app_id,
            defaults={"name": name, "slug": f"game-{steam_app_id}"},
        )
        return game

    def update_session_hours(
        self,
        account: User,
        computer_id: int,
        hours_to_add: float,
        game_id: int = None,
        steam_app_id: int = None,
        game_name: str = None,
    ) -> GameSession:
        """
        Update game session hours from C# app.
        Accepts game_id (preferred) or steam_app_id fallback.
        """
        if hours_to_add < 0:
            raise ValidationError({"hours_to_add": "Hours cannot be negative"})

        game = self._resolve_game(
            game_id=game_id, steam_app_id=steam_app_id, game_name=game_name
        )
        session, _ = self.session_repository.get_or_create_session(
            account=account, game=game, computer_id=computer_id
        )
        session.update_hours(hours_to_add)
        return session

    def start_session(
        self,
        account: User,
        computer_id: int,
        game_id: int = None,
        steam_app_id: int = None,
        game_name: str = None,
    ) -> GameSession:
        """Start a new gaming session"""
        game = self._resolve_game(
            game_id=game_id, steam_app_id=steam_app_id, game_name=game_name
        )
        session, _ = self.session_repository.get_or_create_session(
            account=account, game=game, computer_id=computer_id
        )
        session.start_session()
        return session

    def end_session(
        self,
        account: User,
        computer_id: int,
        hours_played: float = None,
        game_id: int = None,
        steam_app_id: int = None,
    ) -> GameSession:
        """End a gaming session"""
        game = self._resolve_game(game_id=game_id, steam_app_id=steam_app_id)
        session, _ = self.session_repository.get_or_create_session(
            account=account, game=game, computer_id=computer_id
        )
        session.end_session(hours_played=hours_played)
        return session

    def get_account_sessions(self, account: User) -> Dict[str, Any]:
        """Get all sessions for an account with statistics"""
        sessions = self.session_repository.get_by_account(account)

        # Calculate statistics
        stats = sessions.aggregate(
            total_hours=Sum("total_hours_played"),
            total_games=Count("game", distinct=True),
            total_computers=Count("computer", distinct=True),
        )

        return {
            "sessions": sessions,
            "statistics": {
                "total_hours_played": float(stats["total_hours"] or 0),
                "total_games": stats["total_games"],
                "total_computers": stats["total_computers"],
            },
        }

    def get_game_statistics(self) -> List[Dict[str, Any]]:
        """Get overall game statistics for admin dashboard"""
        games = (
            Game.objects.annotate(
                total_hours=Sum("sessions__total_hours_played"),
                total_sessions=Count("sessions"),
                unique_players=Count("sessions__account", distinct=True),
                currently_playing=Count(
                    "sessions", filter=Q(sessions__session_status=SessionStatus.ACTIVE)
                ),
            )
            .values(
                "id",
                "name",
                "app_id",
                "total_hours",
                "total_sessions",
                "unique_players",
                "currently_playing",
            )
            .order_by("-total_hours")
        )

        result = []
        for game in games:
            result.append(
                {
                    "game_id": game["id"],
                    "game_name": game["name"],
                    "app_id": game["app_id"],
                    "total_hours": float(game["total_hours"] or 0),
                    "total_sessions": game["total_sessions"],
                    "unique_players": game["unique_players"],
                    "currently_playing": game["currently_playing"],
                }
            )

        return result

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all currently active gaming sessions"""
        active_sessions = GameSession.objects.filter(
            session_status=SessionStatus.ACTIVE
        ).select_related("account", "computer", "game")

        result = []
        for session in active_sessions:
            # Calculate session duration
            if session.current_session_start:
                duration = timezone.now() - session.current_session_start
                duration_minutes = int(duration.total_seconds() / 60)
            else:
                duration_minutes = 0

            result.append(
                {
                    "session_id": session.id,
                    "user_id": str(session.account.id),
                    "username": session.account.username,
                    "computer_id": session.computer.id,
                    "machine_name": session.computer.name,
                    "game_id": session.game.id,
                    "game_name": session.game.name,
                    "app_id": session.game.app_id,
                    "start_time": session.current_session_start,
                    "duration_minutes": duration_minutes,
                    "total_hours_played": float(session.total_hours_played),
                }
            )

        return result

    def get_user_statistics(self, user) -> Dict[str, Any]:
        """Get user's gaming statistics with top 3 games and order history"""
        from apps.shops.services.implementation.order import OrderService

        # Get sessions data using existing method
        data = self.get_account_sessions(user)
        sessions = data["sessions"]
        statistics = data["statistics"]

        # Get top 3 most played games
        top_sessions = sessions.select_related("game").order_by("-total_hours_played")[
            :3
        ]

        top_games = []
        for session in top_sessions:
            top_games.append(
                {
                    "game_id": session.game.id,
                    "game_name": session.game.name,
                    "app_id": session.game.app_id,
                    "hours_played": float(session.total_hours_played),
                }
            )

        # Get order history
        order_service = OrderService()
        orders = order_service.get_user_orders(user)

        order_history = []
        for order in orders[:10]:  # Last 10 orders
            order_history.append(
                {
                    "order_id": order.id,
                    "status": order.status,
                    "total_price": float(order.total_price),
                    "items_count": order.items.count(),
                    "created_at": order.created_at,
                }
            )

        return {
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
            },
            "total_hours_played": float(statistics["total_hours_played"]),
            "total_games_played": statistics["total_games"],
            "top_games": top_games,
            "total_orders": orders.count(),
            "order_history": order_history,
        }

    def get_computer_games(
        self, computer_id: int = None, hardware_id: str = None, user=None
    ) -> Dict[str, Any]:
        """Get games installed on a specific computer with user stats"""
        from apps.computers.models import Computer, ComputerGame

        # Get computer by ID or hardware_id
        if hardware_id:
            try:
                computer = Computer.objects.get(hardware_id=hardware_id)
            except Computer.DoesNotExist:
                raise ValidationError({"hardware_id": "Computer not found"})
        elif computer_id:
            try:
                computer = Computer.objects.get(id=computer_id)
            except Computer.DoesNotExist:
                raise ValidationError({"computer_id": "Computer not found"})
        else:
            raise ValidationError({"error": "computer_id or hardware_id is required"})

        # Auto-provision: a PC that registered AFTER games were added (or re-registered, e.g.
        # after a DB reset) has NO ComputerGame links → "Игр пока нет", even though the club
        # has games. The Game post_save signal only links games to computers that exist at
        # save time — there's no reverse link for a new computer. Backfill any active games
        # this computer is missing so the catalog appears in the shell.
        try:
            from apps.games.models import Game
            linked = set(
                ComputerGame.objects.filter(computer=computer).values_list("game_id", flat=True)
            )
            missing = Game.objects.filter(is_active=True).exclude(id__in=linked)
            new_links = [
                ComputerGame(computer=computer, game=g, is_installed=True,
                             install_path=g.executable_path or "")
                for g in missing
            ]
            if new_links:
                ComputerGame.objects.bulk_create(new_links, ignore_conflicts=True)
        except Exception:
            pass

        # Get installed games
        computer_games = ComputerGame.objects.filter(
            computer=computer, is_installed=True
        ).select_related("game")

        # Extract games and add hours played from sessions
        games_data = []
        for cg in computer_games:
            game = cg.game

            # Get session hours for this game on this computer for current user
            if user:
                session = GameSession.objects.filter(
                    account=user, game=game, computer=computer
                ).first()
                hours_played = float(session.total_hours_played) if session else 0.0
                last_played = session.last_played if session else None
            else:
                hours_played = 0.0
                last_played = None

            games_data.append(
                {
                    "game": game,
                    "hours_played": hours_played,
                    "last_played": last_played,
                }
            )

        return {
            "computer": computer,
            "games": games_data,
            "total_games": len(games_data),
        }
