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
        """Get user by username (case-insensitive) or exact phone.

        Was case-sensitive `username=` (so 'John' couldn't log in as 'john', though
        registration enforces uniqueness case-insensitively), and a bare OR on phone let
        a value equal to ANOTHER account's phone resolve to that account. Prefer an exact
        username match before falling back to the phone match.
        """
        from django.db.models import Q
        qs = self.model.objects.filter(Q(username__iexact=username) | Q(phone=username))
        return qs.filter(username__iexact=username).first() or qs.first()

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
