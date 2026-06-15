from typing import Optional, Protocol

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.computers.models import Computer

User = get_user_model()


class IComputerRepository(Protocol):
    """Interface for Computer repository"""

    def get_all(self, is_active: Optional[bool] = None) -> QuerySet[Computer]:
        """Get all computers, optionally filtered by active status"""
        ...

    def get_by_id(self, computer_id: int) -> Optional[Computer]:
        """Get computer by ID"""
        ...

    def get_by_slug(self, slug: str) -> Optional[Computer]:
        """Get computer by slug"""
        ...

    def get_by_owner(self, owner: User) -> QuerySet[Computer]:
        """Get all computers owned by a user"""
        ...

    def get_online_computers(self) -> QuerySet[Computer]:
        """Get all online computers"""
        ...

    def create(self, **data) -> Computer:
        """Create a new computer"""
        ...

    def update(self, computer: Computer, **data) -> Computer:
        """Update existing computer"""
        ...

    def delete(self, computer: Computer) -> None:
        """Delete a computer"""
        ...
