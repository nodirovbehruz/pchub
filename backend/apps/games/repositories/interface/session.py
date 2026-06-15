from typing import Optional, Protocol

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.games.models import Game, GameSession

User = get_user_model()


class IGameSessionRepository(Protocol):
    """Interface for GameSession repository"""

    def get_all(self) -> QuerySet[GameSession]:
        """Get all game sessions"""
        ...

    def get_by_id(self, session_id: int) -> Optional[GameSession]:
        """Get session by ID"""
        ...

    def get_by_account(self, account: User) -> QuerySet[GameSession]:
        """Get all sessions for an account"""
        ...

    def get_by_computer(self, computer_id: int) -> QuerySet[GameSession]:
        """Get all sessions for a computer"""
        ...

    def get_by_game(self, game: Game) -> QuerySet[GameSession]:
        """Get all sessions for a game"""
        ...

    def get_active_sessions(self) -> QuerySet[GameSession]:
        """Get all currently active sessions"""
        ...

    def get_or_create_session(
        self, account: User, game: Game, computer_id: int
    ) -> tuple[GameSession, bool]:
        """Get or create a game session"""
        ...

    def create(self, **data) -> GameSession:
        """Create a new game session"""
        ...

    def update(self, session: GameSession, **data) -> GameSession:
        """Update existing session"""
        ...

    def delete(self, session: GameSession) -> None:
        """Delete a session"""
        ...
