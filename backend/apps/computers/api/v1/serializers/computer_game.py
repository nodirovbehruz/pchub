from rest_framework import serializers

from apps.computers.models import ComputerGame
from apps.games.api.v1.serializers.session import GameSimpleSerializer


class ComputerGameSerializer(serializers.ModelSerializer):
    """Serializer for reading installed games on a computer"""

    game = GameSimpleSerializer(read_only=True)
    computer_name = serializers.CharField(source="computer.name", read_only=True)

    class Meta:
        model = ComputerGame
        fields = [
            "id",
            "computer_name",
            "game",
            "is_installed",
            "install_path",
            "install_size_gb",
            "installed_at",
            "last_played",
        ]
        read_only_fields = fields


class ComputerGameCreateSerializer(serializers.Serializer):
    """
    Serializer for C# app to add/update installed game on computer
    Simple JSON format for easy C# integration
    """

    computer_id = serializers.IntegerField(
        required=True, help_text="ID of the computer"
    )
    steam_app_id = serializers.IntegerField(
        required=True, help_text="Steam App ID of the game"
    )
    game_name = serializers.CharField(
        required=False,
        max_length=255,
        help_text="Game name (for auto-creation if game doesn't exist)",
    )
    is_installed = serializers.BooleanField(
        default=True, help_text="Is the game currently installed?"
    )
    install_path = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Installation path on the computer",
    )
    install_size_gb = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=10,
        decimal_places=2,
        min_value=0,
        help_text="Installation size in GB",
    )


class ComputerGameUpdateSerializer(serializers.Serializer):
    """Serializer for updating game installation status"""

    is_installed = serializers.BooleanField(required=False)
    install_path = serializers.CharField(required=False, max_length=500)
    install_size_gb = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0
    )


class InstalledGamesListSerializer(serializers.Serializer):
    """
    Serializer for C# app to send bulk list of installed games
    Useful for syncing all installed games at once
    """

    computer_id = serializers.IntegerField(required=True)
    games = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of installed games with steam_app_id and optional details",
    )

    def validate_games(self, value):
        """Validate each game entry has required fields"""
        for game in value:
            if "steam_app_id" not in game:
                raise serializers.ValidationError("Each game must have 'steam_app_id'")
        return value
