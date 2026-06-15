from typing import Any, Dict, List, Protocol

from apps.computers.models import ComputerGame


class IComputerGameService(Protocol):
    """Interface for ComputerGame service - handles game installation tracking"""

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
        ...

    def remove_installed_game(
        self, computer_id: int, steam_app_id: int
    ) -> ComputerGame:
        """Mark a game as uninstalled"""
        ...

    def get_installed_games(
        self, computer_id: int, installed_only: bool = True
    ) -> Dict[str, Any]:
        """Get all installed games for a computer"""
        ...

    def sync_installed_games(
        self, computer_id: int, games_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Sync installed games list from C# app
        Useful for bulk updates
        """
        ...

    def update_game_install_info(
        self,
        computer_id: int,
        steam_app_id: int,
        install_path: str = None,
        install_size_gb: float = None,
    ) -> ComputerGame:
        """Update game installation details"""
        ...

    def get_installed_games_with_user_stats(
        self, computer_id: int, user, installed_only: bool = True
    ) -> Dict[str, Any]:
        """Get installed games with user play statistics"""
        ...
