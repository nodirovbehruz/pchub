from rest_framework import serializers

from apps.games.models import Game, Tag
from apps.games.models.game import Category


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class GameSerializer(serializers.ModelSerializer):
    """Simple game serializer for general use"""

    icon = serializers.SerializerMethodField()
    header_image = serializers.SerializerMethodField()
    text_image = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = [
            "id",
            "platform",
            "app_id",
            "executable_path",
            "arguments",
            "name",
            "slug",
            "icon",
            "header_image",
            "text_image",
            "developer",
            "publisher",
            "tags",
        ]

    def _fallback(self, obj, kind, w, h):
        return f"https://picsum.photos/seed/game-{obj.id}-{kind}/{w}/{h}"

    def get_icon(self, obj):
        if obj.icon:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.icon.url) if request else obj.icon.url
        return self._fallback(obj, "icon", 64, 64)

    def get_header_image(self, obj):
        if getattr(obj, "header_image_url", ""):
            return obj.header_image_url
        if obj.header_image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.header_image.url) if request else obj.header_image.url
        return self._fallback(obj, "header", 600, 900)

    def get_text_image(self, obj):
        if obj.text_image:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.text_image.url) if request else obj.text_image.url
        return self._fallback(obj, "logo", 256, 384)


class GameListSerializer(serializers.ModelSerializer):
    """Game list serializer - lightweight for listing"""

    total_players = serializers.IntegerField(read_only=True)
    total_hours_played = serializers.FloatField(read_only=True)
    icon = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True,
    )
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Game
        fields = [
            "id",
            "platform",
            "app_id",
            "name",
            "slug",
            "icon",
            "cover",
            "header_image_url",
            "category",
            "category_name",
            "developer",
            "publisher",
            "release_date",
            "version",
            "is_active",
            "total_players",
            "total_hours_played",
        ]
        read_only_fields = ["id", "slug"]

    def _abs(self, obj_field):
        request = self.context.get("request")
        return request.build_absolute_uri(obj_field.url) if request else obj_field.url

    def get_icon(self, obj):
        if obj.icon:
            return self._abs(obj.icon)
        return f"https://picsum.photos/seed/game-{obj.id}-icon/64/64"

    def get_cover(self, obj):
        # Prefer external cover URL, then uploaded header, then icon, then placeholder.
        if getattr(obj, "header_image_url", ""):
            return obj.header_image_url
        if obj.header_image:
            return self._abs(obj.header_image)
        if obj.icon:
            return self._abs(obj.icon)
        return f"https://picsum.photos/seed/game-{obj.id}-cover/300/400"


class GameDetailSerializer(serializers.ModelSerializer):
    """Game detail serializer - comprehensive for single game view"""

    total_players = serializers.IntegerField(read_only=True)
    total_hours_played = serializers.FloatField(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Game
        fields = [
            "id",
            "platform",
            "app_id",
            "executable_path",
            "arguments",
            "name",
            "slug",
            "description",
            "icon",
            "header_image",
            "developer",
            "publisher",
            "release_date",
            "is_active",
            "tags",
            "total_players",
            "total_hours_played",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "created_at", "updated_at",
            "total_players", "total_hours_played",
        ]


class GameCreateSerializer(serializers.ModelSerializer):
    """Game create serializer - for admin game creation"""

    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Game
        fields = [
            "platform",
            "app_id",
            "executable_path",
            "arguments",
            "version",
            "name",
            "slug",
            "description",
            "icon",
            "header_image",
            "header_image_url",
            "category",
            "developer",
            "publisher",
            "release_date",
            "is_active",
        ]

    def validate(self, data):
        platform = data.get("platform", "steam")
        if platform == "steam" and not data.get("app_id"):
            raise serializers.ValidationError(
                {"app_id": "App ID is required for Steam games."}
            )
        if platform == "local" and not data.get("executable_path"):
            raise serializers.ValidationError(
                {"executable_path": "Executable path is required for local games."}
            )
        return data

    def validate_app_id(self, value):
        if value and Game.objects.filter(app_id=value).exists():
            raise serializers.ValidationError("A game with this App ID already exists.")
        return value


class GameUpdateSerializer(serializers.ModelSerializer):
    """Game update serializer - for admin game updates"""

    # app_id must be EDITABLE: a Steam game created without an App ID could never
    # be fixed via the UI (the value was silently stripped) and install commands
    # kept failing. Allow blank/optional so non-Steam games stay unaffected.
    app_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    slug = serializers.SlugField(required=False)

    def validate_app_id(self, value):
        # app_id must stay unique — Create enforced this but Update did not, so two
        # games could share an app_id and GameSession resolution (.get(app_id=...))
        # then raised MultipleObjectsReturned → HTTP 500 on every shell session ping.
        if value:
            qs = Game.objects.filter(app_id=value)
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("A game with this App ID already exists.")
        return value

    class Meta:
        model = Game
        fields = [
            "platform",
            "app_id",
            "executable_path",
            "arguments",
            "name",
            "slug",
            "description",
            "icon",
            "header_image",
            "header_image_url",
            "category",
            "developer",
            "publisher",
            "release_date",
            "version",
            "is_active",
        ]
        read_only_fields = []


class GameBulkImportSerializer(serializers.Serializer):
    """Serializer for bulk importing games"""

    games = serializers.ListField(
        child=serializers.DictField(), help_text="List of game objects to import"
    )

    def validate_games(self, value):
        for game_data in value:
            required_fields = ["app_id", "name"]
            for field in required_fields:
                if field not in game_data:
                    raise serializers.ValidationError(
                        f"Each game must have: {', '.join(required_fields)}"
                    )
        return value
