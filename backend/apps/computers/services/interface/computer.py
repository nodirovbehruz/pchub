from typing import Any, Dict, Protocol

from django.contrib.auth import get_user_model

from apps.computers.models import Computer

User = get_user_model()


class IComputerService(Protocol):
    """Interface for Computer service"""

    def register_computer(self, data: Dict[str, Any]) -> Computer:
        """Register a new computer from C# app"""
        ...

    def update_computer_specs(self, computer_id: int, data: Dict[str, Any]) -> Computer:
        """Update computer hardware specifications"""
        ...

    def get_computer_overview(self, computer_id: int) -> Dict[str, Any]:
        """Get complete computer overview with stats"""
        ...

    def heartbeat(self, computer_id: int) -> Dict[str, Any]:
        """Update computer heartbeat - set status to ONLINE and update last_seen"""
        ...

    def get_all_computers_status(self) -> list:
        """Get all computers with their current status and active sessions"""
        ...
