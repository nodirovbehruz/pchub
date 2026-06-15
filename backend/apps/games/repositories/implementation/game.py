from typing import Optional

from django.db.models import QuerySet

from apps.games.models import Game
from apps.games.repositories.interface.game import IGameRepository


class GameRepository(IGameRepository):
    """Repository for Game model"""

    def __init__(self):
        self.model = Game

    def get_all(self, is_active: Optional[bool] = None) -> QuerySet[Game]:
        """Get all games, optionally filtered by active status"""
        queryset = self.model.objects.all()
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        return queryset.order_by("name")

    def get_by_id(self, game_id: int) -> Optional[Game]:
        """Get game by ID"""
        try:
            return self.model.objects.get(id=game_id)
        except self.model.DoesNotExist:
            return None

    def get_by_steam_id(self, steam_app_id: int) -> Optional[Game]:
        """Get game by App ID (steam_app_id alias)"""
        try:
            return self.model.objects.get(app_id=str(steam_app_id))
        except self.model.DoesNotExist:
            return None

    def get_by_slug(self, slug: str) -> Optional[Game]:
        """Get game by slug"""
        try:
            return self.model.objects.get(slug=slug)
        except self.model.DoesNotExist:
            return None

    def create(self, **data) -> Game:
        """Create a new game"""
        return self.model.objects.create(**data)

    def update(self, game: Game, **data) -> Game:
        """Update existing game"""
        for key, value in data.items():
            setattr(game, key, value)
        game.save()
        return game

    def delete(self, game: Game) -> None:
        """Delete a game"""
        game.delete()

    def get_or_create_by_steam_id(
        self, steam_app_id: int, defaults: dict = None
    ) -> tuple[Game, bool]:
        """Get or create game by App ID (steam_app_id alias → app_id field)"""
        if defaults is None:
            defaults = {}
        return self.model.objects.get_or_create(
            app_id=str(steam_app_id), defaults=defaults
        )
