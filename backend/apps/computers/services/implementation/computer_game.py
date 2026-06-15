from typing import Any, Dict, List

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.computers.models import ComputerGame
from apps.computers.repositories.implementation.computer import ComputerRepository
from apps.computers.repositories.implementation.computer_game import (
    ComputerGameRepository,
)
from apps.computers.repositories.interface.computer import IComputerRepository
from apps.computers.repositories.interface.computer_game import IComputerGameRepository
from apps.computers.services.interface.computer_game import IComputerGameService
from apps.games.repositories.implementation.game import GameRepository
from apps.games.repositories.interface.game import IGameRepository


class ComputerGameService(IComputerGameService):
    """Service for ComputerGame - handles game installation tracking"""

    def __init__(
        self,
        computer_game_repository: IComputerGameRepository = None,
        computer_repository: IComputerRepository = None,
        game_repository: IGameRepository = None,
    ):
        self.computer_game_repository = (
            computer_game_repository or ComputerGameRepository()
        )
        self.computer_repository = computer_repository or ComputerRepository()
        self.game_repository = game_repository or GameRepository()

    def add_installed_game(
        self,
        computer_id: int,
        steam_app_id: int,
        game_name: str = None,
        install_path: str = None,
        install_size_gb: float = None,
    ) -> ComputerGame:
        """
        Add or update an installed game on a computer
        Creates game if doesn't exist
        """
        # Get computer
        computer = self.computer_repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        # Get or create game
        game, created = self.game_repository.get_or_create_by_steam_id(
            steam_app_id=steam_app_id,
            defaults={
                "name": game_name or f"Game {steam_app_id}",
                "slug": f"game-{steam_app_id}",
            },
        )

        # Get or create computer game
        computer_game, created = self.computer_game_repository.get_or_create(
            computer=computer,
            game=game,
            defaults={
                "is_installed": True,
                "install_path": install_path or "",
                "install_size_gb": install_size_gb,
            },
        )

        # Update if already exists
        if not created:
            update_data = {"is_installed": True, "last_played": timezone.now()}
            if install_path:
                update_data["install_path"] = install_path
            if install_size_gb is not None:
                update_data["install_size_gb"] = install_size_gb

            computer_game = self.computer_game_repository.update(
                computer_game, **update_data
            )

        return computer_game

    def remove_installed_game(
        self, computer_id: int, steam_app_id: int
    ) -> ComputerGame:
        """Mark a game as uninstalled"""
        # Get computer
        computer = self.computer_repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        # Get game
        game = self.game_repository.get_by_steam_id(steam_app_id)
        if not game:
            raise ValidationError({"steam_app_id": "Game not found"})

        # Mark as uninstalled
        computer_game = self.computer_game_repository.mark_uninstalled(computer, game)
        if not computer_game:
            raise ValidationError({"error": "Game not installed on this computer"})

        return computer_game

    def get_installed_games(
        self, computer_id: int, installed_only: bool = True
    ) -> Dict[str, Any]:
        """Get all installed games for a computer"""
        # Get computer
        computer = self.computer_repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        # Get games
        games = self.computer_game_repository.get_by_computer(
            computer=computer, installed_only=installed_only
        )

        # Calculate stats
        total_size = sum(
            float(game.install_size_gb or 0) for game in games if game.is_installed
        )

        return {
            "computer_id": computer_id,
            "computer_name": computer.name,
            "installed_games": games.filter(is_installed=True),
            "total_games": games.filter(is_installed=True).count(),
            "total_size_gb": total_size,
            "all_games": games if not installed_only else None,
        }

    def sync_installed_games(
        self, computer_id: int, games_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Sync installed games list from C# app
        Useful for bulk updates
        """
        # Get computer
        computer = self.computer_repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        added = []
        updated = []
        errors = []

        for game_data in games_list:
            try:
                steam_app_id = game_data.get("steam_app_id")
                if not steam_app_id:
                    errors.append({"error": "Missing steam_app_id", "data": game_data})
                    continue

                computer_game = self.add_installed_game(
                    computer_id=computer_id,
                    steam_app_id=steam_app_id,
                    game_name=game_data.get("game_name"),
                    install_path=game_data.get("install_path"),
                    install_size_gb=game_data.get("install_size_gb"),
                )

                if computer_game.installed_at == timezone.now().date():
                    added.append(computer_game)
                else:
                    updated.append(computer_game)

            except Exception as e:
                errors.append(
                    {"error": str(e), "steam_app_id": game_data.get("steam_app_id")}
                )

        return {
            "computer_id": computer_id,
            "added_count": len(added),
            "updated_count": len(updated),
            "error_count": len(errors),
            "added_games": added,
            "updated_games": updated,
            "errors": errors,
        }

    def update_game_install_info(
        self,
        computer_id: int,
        steam_app_id: int,
        install_path: str = None,
        install_size_gb: float = None,
    ) -> ComputerGame:
        """Update game installation details"""
        # Get computer
        computer = self.computer_repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        # Get game
        game = self.game_repository.get_by_steam_id(steam_app_id)
        if not game:
            raise ValidationError({"steam_app_id": "Game not found"})

        # Get computer game
        computer_games = self.computer_game_repository.get_by_computer(computer)
        computer_game = computer_games.filter(game=game).first()

        if not computer_game:
            raise ValidationError({"error": "Game not found on this computer"})

        # Update
        update_data = {}
        if install_path is not None:
            update_data["install_path"] = install_path
        if install_size_gb is not None:
            update_data["install_size_gb"] = install_size_gb

        if update_data:
            computer_game = self.computer_game_repository.update(
                computer_game, **update_data
            )

        return computer_game

    def get_installed_games_with_user_stats(
        self, computer_id: int, user, installed_only: bool = True
    ) -> Dict[str, Any]:
        """Get installed games with user play statistics"""
        from apps.games.models import GameSession

        # Get base installed games data
        data = self.get_installed_games(
            computer_id=computer_id, installed_only=installed_only
        )

        # Build games list with user statistics
        games_with_stats = []
        for computer_game in data["installed_games"]:
            # Get user's session for this game
            session = GameSession.objects.filter(
                account=user, game=computer_game.game, computer_id=computer_id
            ).first()

            game_data = {
                "computer_game": computer_game,
                "user_total_hours": float(session.total_hours_played) if session else 0,
                "user_last_played": session.last_played if session else None,
                "user_total_sessions": 1 if session else 0,
            }
            games_with_stats.append(game_data)

        return {
            "computer_id": data["computer_id"],
            "computer_name": data["computer_name"],
            "total_games": data["total_games"],
            "total_size_gb": data["total_size_gb"],
            "games_with_stats": games_with_stats,
        }
