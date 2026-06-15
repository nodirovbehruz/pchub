from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.games.models import Game, GameSession, SessionStatus
from apps.games.repositories.interface.session import IGameSessionRepository

User = get_user_model()


class GameSessionRepository(IGameSessionRepository):
    """Repository for GameSession model"""

    def __init__(self):
        self.model = GameSession

    def get_all(self) -> QuerySet[GameSession]:
        """Get all game sessions"""
        return self.model.objects.select_related("account", "game", "computer").all()

    def get_by_id(self, session_id: int) -> Optional[GameSession]:
        """Get session by ID"""
        try:
            return self.model.objects.select_related("account", "game", "computer").get(
                id=session_id
            )
        except self.model.DoesNotExist:
            return None

    def get_by_account(self, account: User) -> QuerySet[GameSession]:
        """Get all sessions for an account"""
        return (
            self.model.objects.filter(account=account)
            .select_related("game", "computer")
            .order_by("-last_played")
        )

    def get_by_computer(self, computer_id: int) -> QuerySet[GameSession]:
        """Get all sessions for a computer"""
        return (
            self.model.objects.filter(computer_id=computer_id)
            .select_related("account", "game")
            .order_by("-last_played")
        )

    def get_by_game(self, game: Game) -> QuerySet[GameSession]:
        """Get all sessions for a game"""
        return (
            self.model.objects.filter(game=game)
            .select_related("account", "computer")
            .order_by("-last_played")
        )

    def get_active_sessions(self) -> QuerySet[GameSession]:
        """Get all currently active sessions"""
        return self.model.objects.filter(
            session_status=SessionStatus.ACTIVE
        ).select_related("account", "game", "computer")

    def get_or_create_session(
        self, account: User, game: Game, computer_id: int
    ) -> tuple[GameSession, bool]:
        """Get or create a game session"""
        return self.model.objects.get_or_create(
            account=account, game=game, computer_id=computer_id
        )

    def create(self, **data) -> GameSession:
        """Create a new game session"""
        return self.model.objects.create(**data)

    def update(self, session: GameSession, **data) -> GameSession:
        """Update existing session"""
        for key, value in data.items():
            setattr(session, key, value)
        session.save()
        return session

    def delete(self, session: GameSession) -> None:
        """Delete a session"""
        session.delete()
