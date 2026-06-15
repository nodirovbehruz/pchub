from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.computers.models import Computer, ComputerStatus
from apps.computers.repositories.interface.computer import IComputerRepository

User = get_user_model()


class ComputerRepository(IComputerRepository):
    """Repository for Computer model"""

    def __init__(self):
        self.model = Computer

    def get_all(self, is_active: Optional[bool] = None) -> QuerySet[Computer]:
        """Get all computers, optionally filtered by active status"""
        queryset = self.model.objects.all()
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset.order_by("-last_seen", "name")

    def get_by_id(self, computer_id: int) -> Optional[Computer]:
        """Get computer by ID"""
        try:
            return self.model.objects.get(id=computer_id)
        except self.model.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> Optional[Computer]:
        """Get computer by slug"""
        try:
            return self.model.objects.get(slug=slug)
        except self.model.DoesNotExist:
            return None

    def get_by_owner(self, owner: User) -> QuerySet[Computer]:
        """Get all computers owned by a user"""
        return self.model.objects.filter(owner=owner).order_by("-last_seen", "name")

    def get_online_computers(self) -> QuerySet[Computer]:
        """Get all online computers"""
        return self.model.objects.filter(
            status=ComputerStatus.ONLINE, is_active=True
        ).order_by("name")

    def create(self, **data) -> Computer:
        """Create a new computer"""
        return self.model.objects.create(**data)

    def update(self, computer: Computer, **data) -> Computer:
        """Update existing computer"""
        for key, value in data.items():
            setattr(computer, key, value)
        computer.save()
        return computer

    def delete(self, computer: Computer) -> None:
        """Delete a computer"""
        computer.delete()
