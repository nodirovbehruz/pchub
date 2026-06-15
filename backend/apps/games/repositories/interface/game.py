from typing import Optional, Protocol

from django.db.models import QuerySet

from apps.games.models import Game


class IGameRepository(Protocol):
    """Interface for Game repository"""

    def get_all(self, is_active: Optional[bool] = None) -> QuerySet[Game]:
        """Get all games, optionally filtered by active status"""
        ...

    def get_by_id(self, game_id: int) -> Optional[Game]:
        """Get game by ID"""
        ...

    def get_by_steam_id(self, steam_app_id: int) -> Optional[Game]:
        """Get game by Steam App ID"""
        ...

    def get_by_slug(self, slug: str) -> Optional[Game]:
        """Get game by slug"""
        ...

    def create(self, **data) -> Game:
        """Create a new game"""
        ...

    def update(self, game: Game, **data) -> Game:
        """Update existing game"""
        ...

    def delete(self, game: Game) -> None:
        """Delete a game"""
        ...

    def get_or_create_by_steam_id(
        self, steam_app_id: int, defaults: dict = None
    ) -> tuple[Game, bool]:
        """Get or create game by Steam App ID"""
        ...
