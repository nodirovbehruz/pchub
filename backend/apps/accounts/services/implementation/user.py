from typing import Any

from apps.accounts.models import CustomUser
from apps.accounts.repositories.interface.account import IAccountRepository
from apps.accounts.services.interface.user import IUserCreateService


class UserCreateService(IUserCreateService):
    """User create service implementation"""

    def __init__(self, repository: IAccountRepository):
        self.repository = repository

    def execute(self, data: dict[str, Any]) -> CustomUser:
        """Create a new user.

        Self-registration via the personal cabinet → user_type = 'owner'.
        Regular clients are created by admins, not via this endpoint.
        """
        data.pop("password_confirm")
        data.setdefault("user_type", "owner")  # self-registered = club owner

        return self.repository.create_user(data)
