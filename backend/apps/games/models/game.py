from django.db import models
from django.utils.translation import gettext_lazy as _


class GamePlatform(models.TextChoices):
    STEAM = "steam", _("Steam")
    EPIC = "epic", _("Epic Games")
    RIOT = "riot", _("Riot Games")
    BATTLENET = "battlenet", _("Battle.net")
    ORIGIN = "origin", _("Origin / EA app")
    UBISOFT = "ubisoft", _("Ubisoft Connect")
    ROCKSTAR = "rockstar", _("Rockstar Games Launcher")
    LOCAL = "local", _("Local App (No DRM)")


class Category(models.Model):
    name = models.CharField(max_length=255, verbose_name="Имя категории")
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Категория игр/приложений"
        verbose_name_plural = "Категории игр/приложений"
        ordering = ["order"]

    def __str__(self):
        return self.name


class Game(models.Model):
    """Game model - stores information about games (Steam and local)"""

    # Content Management
    is_senet_library = models.BooleanField(
        default=False, 
        verbose_name="Из Библиотеки SENET",
        help_text="Официальная карточка SENET, защищена от перезаписи ключей."
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Категория"
    )

    # Game Type / Platform
    platform = models.CharField(
        max_length=20,
        choices=GamePlatform.choices,
        default=GamePlatform.STEAM,
        verbose_name="Платформа запуска"
    )

    # Identifiers
    app_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="App ID (Steam/Epic/etc)",
        help_text="Внутренний идентификатор игры во внешнем DRM"
    )

    # Local game executable path
    executable_path = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text=_(
            "Full path to game executable (local games only, e.g. C:\\Games\\game.exe)"
        ),
    )

    # Command line arguments
    arguments = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text=_("Command line arguments for the game (e.g. --incognito for Chrome)"),
    )

    # Target version — PCs whose installed_version differs get an auto-update.
    version = models.CharField(
        max_length=50, default="1.0", blank=True,
        help_text=_("Target version; bump it to roll an update to every PC."),
    )

    # Basic Information
    name = models.CharField(max_length=255, help_text=_("Game name"))
    slug = models.SlugField(
        max_length=255, unique=True, help_text=_("URL-friendly game name")
    )
    description = models.TextField(blank=True, help_text=_("Game description"))

    # Media
    icon = models.ImageField(
        upload_to="games/icons/", blank=True, null=True, help_text=_("Game icon")
    )
    header_image = models.ImageField(
        upload_to="games/headers/",
        blank=True,
        null=True,
        help_text=_("Header/banner image"),
    )
    header_image_url = models.URLField(
        max_length=1000, blank=True, default="",
        help_text=_("External cover URL (used when no uploaded header_image)."),
    )
    text_image = models.ImageField(
        upload_to="games/text_logos/",
        blank=True,
        null=True,
        help_text=_(
            "Stylized text/logo image shown as the game title on the dashboard"
        ),
    )

    # Tags/Genres
    tags = models.ManyToManyField(
        "games.Tag", related_name="games", blank=True, help_text=_("Game tags/genres")
    )

    # Metadata
    developer = models.CharField(
        max_length=255, blank=True, help_text=_("Game developer")
    )
    publisher = models.CharField(
        max_length=255, blank=True, help_text=_("Game publisher")
    )
    release_date = models.DateField(null=True, blank=True, help_text=_("Release date"))

    # Status
    is_active = models.BooleanField(default=True, help_text=_("Is game active?"))

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games"
        verbose_name = _("Game")
        verbose_name_plural = _("Games")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["app_id"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_platform_display()})"

    @property
    def total_players(self):
        """Get total number of unique players"""
        return self.sessions.values("account").distinct().count()

    @property
    def total_hours_played(self):
        """Get total hours played across all sessions"""
        from django.db.models import Sum

        result = self.sessions.aggregate(total=Sum("total_hours_played"))
        return result["total"] or 0
