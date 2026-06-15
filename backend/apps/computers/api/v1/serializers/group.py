from rest_framework import serializers

from apps.computers.models import ComputerGroup


class ComputerGroupSerializer(serializers.ModelSerializer):
    computers_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ComputerGroup
        fields = (
            "id",
            "club",
            "name",
            "slug",
            "color",
            "position",
            "is_active",
            "computers_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "club", "created_at", "updated_at", "computers_count")  # club: no cross-tenant re-assign
