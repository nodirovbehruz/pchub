from typing import Any

from django.db.models import QuerySet

from apps.accounts.models import CustomUser
from apps.accounts.repositories.interface.account import IAccountRepository


class AccountRepository(IAccountRepository):
    """Account repository implementation"""

    def __init__(self, model: CustomUser = CustomUser):
        self.model = model

    def get_users(self) -> QuerySet[CustomUser]:
        """Get all users"""
        return self.model.objects.filter(
            is_active=True,
        )

    def get_user_by_username(self, username: str) -> CustomUser:
        """Get user by username or phone"""
        from django.db.models import Q
        return self.model.objects.filter(Q(username=username) | Q(phone=username)).first()

    def create_user(self, data: dict[str, Any]) -> CustomUser:
        """Create a new user"""
        return self.model.objects.create_user(**data)

    def update_user(self, user_id: int, data: dict[str, Any]) -> CustomUser:
        """Update an existing user"""
        user = self.model.objects.get(id=user_id)
        for key, value in data.items():
            setattr(user, key, value)
        user.save()
        return user

    def none(self) -> QuerySet[CustomUser, CustomUser]:
        """Return None"""
        return CustomUser.objects.none()
