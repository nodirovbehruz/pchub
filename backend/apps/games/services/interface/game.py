from typing import Any, Dict, Optional, Protocol

from django.db.models import QuerySet

from apps.games.models import Game


class IGameListService(Protocol):
    """Interface for Game list service"""

    def execute(self, is_active: bool = True) -> QuerySet[Game]:
        """List all games with filtering"""
        ...


class IGameDetailService(Protocol):
    """Interface for Game detail service"""

    def execute(self, slug: str) -> Optional[Game]:
        """Get game by slug"""
        ...


class IGameCreateService(Protocol):
    """Interface for Game create service"""

    def execute(self, data: Dict[str, Any]) -> Game:
        """Create new game"""
        ...


class IGameUpdateService(Protocol):
    """Interface for Game update service"""

    def execute(self, slug: str, data: Dict[str, Any]) -> Game:
        """Update game"""
        ...


class IGameDeleteService(Protocol):
    """Interface for Game delete service"""

    def execute(self, slug: str) -> None:
        """Delete/deactivate game"""
        ...
