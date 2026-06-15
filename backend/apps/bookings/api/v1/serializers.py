from rest_framework import serializers

from apps.bookings.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    starts_in_minutes = serializers.IntegerField(read_only=True)
    client_username = serializers.CharField(source="client.username", read_only=True)
    host_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="hosts", read_only=True,
    )

    class Meta:
        model = Booking
        fields = [
            "id", "club",
            "client", "client_username",
            "guest_name", "guest_phone",
            "hosts", "host_ids",
            "from_at", "to_at",
            "status", "comment", "hard_booking",
            "starts_in_minutes",
            "created_by", "created_at", "updated_at",
        ]
        # club is set server-side from the authorized tenant (see the view) — never
        # trusted from the request body. created_by likewise.
        read_only_fields = ["id", "club", "created_by", "created_at", "updated_at"]
