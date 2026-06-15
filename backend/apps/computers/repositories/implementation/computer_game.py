from typing import Optional

from django.db.models import QuerySet

from apps.computers.models import Computer, ComputerGame
from apps.computers.repositories.interface.computer_game import IComputerGameRepository
from apps.games.models import Game


class ComputerGameRepository(IComputerGameRepository):
    """Repository for ComputerGame model"""

    def __init__(self):
        self.model = ComputerGame

    def get_all(self) -> QuerySet[ComputerGame]:
        """Get all computer games"""
        return self.model.objects.select_related("computer", "game").all()

    def get_by_id(self, computer_game_id: int) -> Optional[ComputerGame]:
        """Get computer game by ID"""
        try:
            return self.model.objects.select_related("computer", "game").get(
                id=computer_game_id
            )
        except self.model.DoesNotExist:
            return None

    def get_by_computer(
        self, computer: Computer, installed_only: bool = False
    ) -> QuerySet[ComputerGame]:
        """Get all games for a computer"""
        queryset = self.model.objects.filter(computer=computer).select_related("game")

        if installed_only:
            queryset = queryset.filter(is_installed=True)

        return queryset.order_by("-last_played", "game__name")

    def get_by_game(self, game: Game) -> QuerySet[ComputerGame]:
        """Get all computers that have this game"""
        return self.model.objects.filter(game=game).select_related("computer")

    def get_or_create(
        self, computer: Computer, game: Game, defaults: dict = None
    ) -> tuple[ComputerGame, bool]:
        """Get or create computer game installation"""
        if defaults is None:
            defaults = {}

        return self.model.objects.get_or_create(
            computer=computer, game=game, defaults=defaults
        )

    def create(self, **data) -> ComputerGame:
        """Create a new computer game entry"""
        return self.model.objects.create(**data)

    def update(self, computer_game: ComputerGame, **data) -> ComputerGame:
        """Update existing computer game"""
        for key, value in data.items():
            setattr(computer_game, key, value)
        computer_game.save()
        return computer_game

    def delete(self, computer_game: ComputerGame) -> None:
        """Delete a computer game entry"""
        computer_game.delete()

    def mark_uninstalled(
        self, computer: Computer, game: Game
    ) -> Optional[ComputerGame]:
        """Mark a game as uninstalled"""
        try:
            computer_game = self.model.objects.get(computer=computer, game=game)
            computer_game.is_installed = False
            computer_game.save(update_fields=["is_installed"])
            return computer_game
        except self.model.DoesNotExist:
            return None
