from rest_framework import serializers

from apps.sessions_.models import AdminCall, ClientSession, Review, SessionHost


class SessionHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionHost
        fields = ["id", "computer", "started_at", "finished_at"]


class ClientSessionSerializer(serializers.ModelSerializer):
    hosts = SessionHostSerializer(many=True, read_only=True)
    time_left_minutes = serializers.IntegerField(read_only=True)
    client_username = serializers.CharField(source="client.username", read_only=True)

    class Meta:
        model = ClientSession
        fields = [
            "id", "club",
            "client", "client_username", "guest_session",
            "tariff", "payment", "shift",
            "duration_minutes", "elapsed_minutes", "time_left_minutes",
            "total_cost", "postpaid", "status",
            "hosts",
            "started_at", "finished_at", "cancelled_at",
            "created_at", "updated_at",
        ]
        # club/client/money fields must not be client-writable: leaving them open let a
        # PATCH zero out total_cost, flip postpaid, or move the session to another tenant.
        read_only_fields = ["id", "created_at", "updated_at", "club", "client",
                            "total_cost", "payment", "guest_session"]


class ReviewSerializer(serializers.ModelSerializer):
    client_username = serializers.CharField(source="client.username", read_only=True)
    computer_name = serializers.CharField(source="computer.name", read_only=True)

    def validate_rating(self, value):
        return _validate_rating_1_5(value)

    class Meta:
        model = Review
        fields = [
            "id", "club",
            "client", "client_username",
            "computer", "computer_name",
            "shift", "session",
            "rating", "comment", "contact_info",
            "tip_amount", "tip_admin",
            "is_anonymous", "is_read",
            "created_at",
        ]
        # tip_amount/tip_admin/is_read are STAFF-controlled — a client creating a review
        # must not set them (was writable → a client could self-assign tips / mark read).
        read_only_fields = ["id", "created_at", "tip_amount", "tip_admin", "is_read"]
        extra_kwargs = {
            # Filled server-side from the authenticated user / tenant.
            "client": {"required": False},
            "club": {"required": False},
            "computer": {"required": False},
            "session": {"required": False},
            "shift": {"required": False},
        }


def _validate_rating_1_5(value):
    # Review.rating had no bound (PositiveSmallIntegerField up to ~32767), so a client
    # could POST rating=0 or 9999 and corrupt rating averages shown to staff.
    if value is not None and not (1 <= int(value) <= 5):
        raise serializers.ValidationError("Рейтинг должен быть от 1 до 5")
    return value


class AdminCallSerializer(serializers.ModelSerializer):
    client_username = serializers.CharField(source="client.username", read_only=True, default=None)
    computer_name = serializers.CharField(source="computer.name", read_only=True, default=None)

    class Meta:
        model = AdminCall
        fields = [
            "id", "club", "computer", "computer_name", "client", "client_username", "shift",
            "answered_by", "called_at", "answered_at", "note", "is_answered",
        ]
        # answered_by/answered_at are set by the answer endpoint, not the client body.
        read_only_fields = ["id", "called_at", "is_answered", "answered_by", "answered_at"]
        extra_kwargs = {
            # Filled server-side from the authenticated user / tenant.
            "client": {"required": False},
            "club": {"required": False},
            "computer": {"required": False},
            "shift": {"required": False},
        }
