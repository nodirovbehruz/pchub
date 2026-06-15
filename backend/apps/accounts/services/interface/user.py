from typing import Any, Protocol


class IUserCreateService(Protocol):
    """User create service interface"""

    def execute(self, data: dict[str, Any]):
        """Create a new user

        Args:
            data: User data

        Returns:
            User: Created user
        """
        ...
