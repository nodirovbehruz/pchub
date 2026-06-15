from typing import Any, Dict, Optional

from django.db.models import QuerySet
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.games.models import Game
from apps.games.repositories.implementation.game import GameRepository
from apps.games.repositories.interface.game import IGameRepository
from apps.games.services.interface.game import (
    IGameCreateService,
    IGameDeleteService,
    IGameDetailService,
    IGameListService,
    IGameUpdateService,
)


class GameListService(IGameListService):
    """Game list service implementation"""

    def __init__(self, repository: IGameRepository = None):
        self.repository = repository or GameRepository()

    def execute(self, is_active: bool = True) -> QuerySet[Game]:
        """List all games"""
        return self.repository.get_all(is_active=is_active)


class GameDetailService(IGameDetailService):
    """Game detail service implementation"""

    def __init__(self, repository: IGameRepository = None):
        self.repository = repository or GameRepository()

    def execute(self, slug: str) -> Optional[Game]:
        """Get game by slug"""
        game = self.repository.get_by_slug(slug=slug)
        if not game:
            raise ValidationError({"detail": "Game not found"})
        return game


class GameCreateService(IGameCreateService):
    """Game create service implementation"""

    def __init__(self, repository: IGameRepository = None):
        self.repository = repository or GameRepository()

    def execute(self, data: Dict[str, Any]) -> Game:
        """Create new game with auto-generated slug"""
        # Auto-generate slug if not provided
        if "slug" not in data or not data["slug"]:
            data["slug"] = slugify(data["name"])

        # Ensure slug uniqueness
        original_slug = data["slug"]
        counter = 1
        while self.repository.get_by_slug(data["slug"]):
            data["slug"] = f"{original_slug}-{counter}"
            counter += 1

        return self.repository.create(**data)


class GameUpdateService(IGameUpdateService):
    """Game update service implementation"""

    def __init__(self, repository: IGameRepository = None):
        self.repository = repository or GameRepository()

    def execute(self, slug: str, data: Dict[str, Any]) -> Game:
        """Update game"""
        game = self.repository.get_by_slug(slug=slug)

        if not game:
            raise ValidationError({"detail": "Game not found"})

        # If name is being updated, regenerate slug
        if "name" in data and data["name"] != game.name:
            if "slug" not in data:
                new_slug = slugify(data["name"])
                # Ensure new slug is unique
                original_slug = new_slug
                counter = 1
                while self.repository.get_by_slug(new_slug) and new_slug != slug:
                    new_slug = f"{original_slug}-{counter}"
                    counter += 1
                data["slug"] = new_slug

        return self.repository.update(game, **data)


class GameDeleteService(IGameDeleteService):
    """Game delete service implementation (soft delete via is_active)"""

    def __init__(self, repository: IGameRepository = None):
        self.repository = repository or GameRepository()

    def execute(self, slug: str) -> None:
        """Soft delete game by setting is_active=False"""
        game = self.repository.get_by_slug(slug=slug)

        if not game:
            raise ValidationError({"detail": "Game not found"})

        # Soft delete: set is_active to False
        self.repository.update(game, is_active=False)
