from typing import Optional, Protocol

from django.db.models import QuerySet

from apps.computers.models import Computer, ComputerGame
from apps.games.models import Game


class IComputerGameRepository(Protocol):
    """Interface for ComputerGame repository"""

    def get_all(self) -> QuerySet[ComputerGame]:
        """Get all computer games"""
        ...

    def get_by_id(self, computer_game_id: int) -> Optional[ComputerGame]:
        """Get computer game by ID"""
        ...

    def get_by_computer(
        self, computer: Computer, installed_only: bool = False
    ) -> QuerySet[ComputerGame]:
        """Get all games for a computer"""
        ...

    def get_by_game(self, game: Game) -> QuerySet[ComputerGame]:
        """Get all computers that have this game"""
        ...

    def get_or_create(
        self, computer: Computer, game: Game, defaults: dict = None
    ) -> tuple[ComputerGame, bool]:
        """Get or create computer game installation"""
        ...

    def create(self, **data) -> ComputerGame:
        """Create a new computer game entry"""
        ...

    def update(self, computer_game: ComputerGame, **data) -> ComputerGame:
        """Update existing computer game"""
        ...

    def delete(self, computer_game: ComputerGame) -> None:
        """Delete a computer game entry"""
        ...

    def mark_uninstalled(
        self, computer: Computer, game: Game
    ) -> Optional[ComputerGame]:
        """Mark a game as uninstalled"""
        ...
