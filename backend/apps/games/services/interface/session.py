from typing import Any, Dict, Protocol

from django.contrib.auth import get_user_model

from apps.games.models import GameSession

User = get_user_model()


class IGameSessionService(Protocol):
    """Interface for GameSession service - handles C# app integration"""

    def update_session_hours(
        self, account: User, steam_app_id: int, computer_id: int, hours_to_add: float
    ) -> GameSession:
        """
        Update game session hours from C# app
        Creates game if doesn't exist, creates session if doesn't exist
        """
        ...

    def start_session(
        self, account: User, steam_app_id: int, computer_id: int
    ) -> GameSession:
        """Start a new gaming session"""
        ...

    def end_session(
        self,
        account: User,
        steam_app_id: int,
        computer_id: int,
        hours_played: float = None,
    ) -> GameSession:
        """End a gaming session"""
        ...

    def get_account_sessions(self, account: User) -> Dict[str, Any]:
        """Get all sessions for an account with statistics"""
        ...

    def get_game_statistics(self) -> list:
        """Get overall game statistics for admin dashboard"""
        ...

    def get_active_sessions(self) -> list:
        """Get all currently active gaming sessions"""
        ...

    def get_user_statistics(self, user) -> Dict[str, Any]:
        """Get user's gaming statistics with top 3 games"""
        ...

    def get_computer_games(
        self, computer_id: int = None, hardware_id: str = None, user=None
    ) -> Dict[str, Any]:
        """Get games installed on a specific computer with user stats"""
        ...
