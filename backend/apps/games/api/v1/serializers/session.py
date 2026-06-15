from rest_framework import serializers

from apps.games.models import Game, GameSession


class GameSimpleSerializer(serializers.ModelSerializer):
    """Simple game serializer for nested use"""

    class Meta:
        model = Game
        fields = [
            "id",
            "platform",
            "app_id",
            "executable_path",
            "name",
            "slug",
            "icon",
        ]


class GameSessionSerializer(serializers.ModelSerializer):
    """Serializer for reading game session data"""

    game = GameSimpleSerializer(read_only=True)
    account_username = serializers.CharField(source="account.username", read_only=True)
    computer_name = serializers.CharField(source="computer.name", read_only=True)

    class Meta:
        model = GameSession
        fields = [
            "id",
            "account_username",
            "game",
            "computer_name",
            "total_hours_played",
            "current_session_start",
            "session_status",
            "last_played",
            "created_at",
        ]
        read_only_fields = fields


class GameSessionUpdateSerializer(serializers.Serializer):
    """
    Serializer for C# app to update game session hours.
    Provide either game_id (preferred) or steam_app_id.
    """

    game_id = serializers.IntegerField(
        required=False, help_text="Database ID of the game (preferred)"
    )
    steam_app_id = serializers.IntegerField(
        required=False, help_text="Steam App ID (Steam games only, fallback)"
    )
    computer_id = serializers.IntegerField(
        required=True, help_text="ID of the computer where game is played"
    )
    hours_to_add = serializers.FloatField(
        required=True,
        min_value=0,
        help_text="Hours to add to total (e.g., 0.5 for 30 minutes)",
    )
    game_name = serializers.CharField(
        required=False,
        max_length=255,
        help_text="Optional: Game name for auto-creation",
    )

    def validate(self, data):
        if not data.get("game_id") and not data.get("steam_app_id"):
            raise serializers.ValidationError(
                "Either game_id or steam_app_id must be provided."
            )
        return data


class GameSessionStartSerializer(serializers.Serializer):
    """Serializer for starting a game session from C# app"""

    game_id = serializers.IntegerField(required=False)
    steam_app_id = serializers.IntegerField(required=False)
    computer_id = serializers.IntegerField(required=True)
    game_name = serializers.CharField(required=False, max_length=255)

    def validate(self, data):
        if not data.get("game_id") and not data.get("steam_app_id"):
            raise serializers.ValidationError(
                "Either game_id or steam_app_id must be provided."
            )
        return data


class GameSessionEndSerializer(serializers.Serializer):
    """Serializer for ending a game session from C# app"""

    game_id = serializers.IntegerField(required=False)
    steam_app_id = serializers.IntegerField(required=False)
    computer_id = serializers.IntegerField(required=True)
    hours_played = serializers.FloatField(required=False, min_value=0)

    def validate(self, data):
        if not data.get("game_id") and not data.get("steam_app_id"):
            raise serializers.ValidationError(
                "Either game_id or steam_app_id must be provided."
            )
        return data
