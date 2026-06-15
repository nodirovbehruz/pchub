from rest_framework import serializers

from apps.computers.models import ComputerCommand
from apps.computers.models.command import CommandType


class ComputerCommandSerializer(serializers.ModelSerializer):
    computer_name = serializers.CharField(source="computer.name", read_only=True)
    game_name = serializers.CharField(
        source="game.name", read_only=True, allow_null=True
    )
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True, allow_null=True
    )

    class Meta:
        model = ComputerCommand
        fields = [
            "id",
            "computer",
            "computer_name",
            "game",
            "game_name",
            "command_type",
            "status",
            "payload",
            "error_message",
            "created_by",
            "created_by_username",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "error_message",
            "created_by",
            "created_at",
            "updated_at",
        ]


class ComputerCommandCreateSerializer(serializers.Serializer):
    """Used by admin to create a new command for a specific PC."""

    computer_id = serializers.IntegerField()
    game_id = serializers.IntegerField(required=False, allow_null=True)
    # Accept every command the model/shell understands (install/update + power &
    # control: reboot, shutdown, wol, lock, unlock, login, transfer …), not just
    # the software ones — otherwise power actions fail validation with HTTP 400.
    command_type = serializers.ChoiceField(choices=[c[0] for c in CommandType.choices])
    payload = serializers.JSONField(required=False, default=dict)


class ComputerCommandStatusUpdateSerializer(serializers.Serializer):
    """Used by PC client to report command execution status."""

    status = serializers.ChoiceField(choices=["in_progress", "completed", "failed"])
    error_message = serializers.CharField(required=False, allow_blank=True, default="")
