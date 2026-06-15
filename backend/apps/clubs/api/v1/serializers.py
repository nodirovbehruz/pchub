from rest_framework import serializers

from apps.clubs.models import Club


class ClubSerializer(serializers.ModelSerializer):
    address = serializers.CharField(read_only=True)
    has_shift = serializers.SerializerMethodField()

    class Meta:
        model = Club
        fields = (
            "id",
            "name",
            "site",
            "country",
            "city",
            "timezone",
            "street",
            "house",
            "address",
            "contact_name",
            "contact_phone",
            "club_token",
            "is_trial",
            "trial_until",
            "is_active",
            "has_shift",
            "created_at",
        )
        read_only_fields = ("id", "club_token", "address", "has_shift", "created_at")

    def get_has_shift(self, obj):
        try:
            from apps.billing.models import Shift
            return Shift.objects.filter(club=obj, is_active=True).exists()
        except Exception:
            return False


class ClubCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new club (POST /api/v1/clubs/my/)."""

    class Meta:
        model = Club
        fields = (
            "name",
            "city",
            "street",
            "house",
            "contact_phone",
            "timezone",
        )
        extra_kwargs = {
            "name": {"required": True},
            "city": {"required": False, "allow_blank": True},
            "street": {"required": False, "allow_blank": True},
            "house": {"required": False, "allow_blank": True},
            "contact_phone": {"required": False, "allow_blank": True},
            "timezone": {"required": False},
        }


class ClubUpdateSerializer(serializers.ModelSerializer):
    """Serializer for partial club settings update (PATCH /api/v1/clubs/<id>/)."""

    class Meta:
        model = Club
        fields = (
            "name",
            "site",
            "country",
            "city",
            "timezone",
            "street",
            "house",
            "contact_name",
            "contact_phone",
        )
        extra_kwargs = {f: {"required": False} for f in fields}
