from typing import Any, Protocol

from django.db.models import QuerySet

from apps.accounts.models import CustomUser


class IAccountRepository(Protocol):
    """Account repository interface"""

    def get_user_by_username(self, username: str) -> CustomUser:
        """Get user by username

        Args:
            username: User username

        Returns:
            User: User object
        """
        ...

    def create_user(self, data: dict[str, Any]) -> CustomUser:
        """Create a new user

        Args:
            data: User data

        Returns:
            User: Created user
        """
        ...

    def update_user(self, user_id: int, data: dict[str, Any]) -> CustomUser:
        """Update an existing user

        Args:
            user_id: User ID
            data: User data

        Returns:
            User: Updated user
        """
        ...

    def get_users(self) -> QuerySet[CustomUser]:
        """Get all users

        Returns:
            QuerySet[User, User]: All users
        """
        ...

    def none(self) -> QuerySet[CustomUser, CustomUser]:
        """Return None

        Returns:
            QuerySet[User, User]: None
        """
        ...
