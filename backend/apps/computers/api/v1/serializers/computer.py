from rest_framework import serializers

from apps.computers.models import Computer


class ComputerSerializer(serializers.ModelSerializer):
    """Serializer for reading computer data"""

    owner_username = serializers.CharField(source="owner.username", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    installed_games_count = serializers.SerializerMethodField()
    total_gaming_hours = serializers.SerializerMethodField()
    active_session = serializers.SerializerMethodField()
    next_booking = serializers.SerializerMethodField()

    # ── Bulk-map readers (set via context in list view to avoid N+1) ──
    def get_installed_games_count(self, obj):
        m = self.context.get("games_count_map")
        if m is not None:
            return m.get(obj.id, 0)
        return obj.installed_games_count  # fallback (detail view)

    def get_total_gaming_hours(self, obj):
        m = self.context.get("gaming_hours_map")
        if m is not None:
            return m.get(obj.id, 0)
        return obj.total_gaming_hours  # fallback

    class Meta:
        model = Computer
        fields = [
            "id",
            "name",
            "pc_number",
            "slug",
            "description",
            "hardware_id",
            "owner_username",
            "club",
            "group", "group_name",
            "cpu_model",
            "cpu_cores",
            "cpu_threads",
            "ram_total_gb",
            "gpu_model",
            "storage_total_gb",
            "os_name",
            "os_version",
            "ip_address",
            "mac_address",
            "status",
            "is_active",
            "high_access_active",
            "position_x", "position_y",
            "last_seen",
            "current_app", "shell_version",
            "installed_games_count",
            "total_gaming_hours",
            "active_session", "next_booking",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "pc_number",
            "slug",
            "hardware_id",
            "owner_username",
            "status",
            "high_access_active",
            "last_seen",
            "installed_games_count",
            "total_gaming_hours",
            "active_session", "next_booking",
            "created_at",
        ]

    @staticmethod
    def _ser_session(s):
        if not s:
            return None
        # Synthetic postpaid/guest sessions are passed as a ready dict.
        if isinstance(s, dict):
            return s
        return {
            "id": s.id,
            "client": s.client.username if s.client else None,
            "tariff": s.tariff.name if s.tariff else None,
            "started_at": s.started_at,
            "time_left_minutes": s.time_left_minutes,
        }

    @staticmethod
    def _ser_booking(b):
        if not b:
            return None
        return {
            "id": b.id,
            "client": b.client.username if b.client else (b.guest_name or "guest"),
            "from_at": b.from_at,
            "starts_in_minutes": b.starts_in_minutes,
        }

    def get_active_session(self, obj):
        smap = self.context.get("active_sessions_map")
        if smap is not None:
            return self._ser_session(smap.get(obj.id))
        # Fallback per-object query (detail view)
        try:
            from apps.sessions_.models import ClientSession, ClientSessionStatus
            s = ClientSession.objects.filter(
                hosts__computer=obj, status=ClientSessionStatus.ACTIVE,
            ).select_related("client", "tariff").first()
            return self._ser_session(s)
        except Exception:
            return None

    def get_next_booking(self, obj):
        bmap = self.context.get("bookings_map")
        if bmap is not None:
            return self._ser_booking(bmap.get(obj.id))
        try:
            from apps.bookings.models import Booking, BookingStatus
            from django.utils import timezone
            b = Booking.objects.filter(
                hosts=obj, status=BookingStatus.ACTIVE, to_at__gte=timezone.now(),
            ).order_by("from_at").first()
            return self._ser_booking(b)
        except Exception:
            return None


class ComputerRegistrationSerializer(serializers.Serializer):
    """
    Serializer for C# app to register a new computer
    Simple JSON format for easy C# integration
    """

    name = serializers.CharField(
        required=True, max_length=255, help_text="Computer name/identifier"
    )
    description = serializers.CharField(
        required=False, allow_blank=True, help_text="Computer description"
    )
    hardware_id = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=64,
        help_text="Unique hardware identifier (CPU ID + Motherboard Serial + MAC)",
    )

    # Hardware specifications
    cpu_model = serializers.CharField(required=False, max_length=255)
    cpu_cores = serializers.IntegerField(required=False, min_value=1)
    cpu_threads = serializers.IntegerField(required=False, min_value=1)
    ram_total_gb = serializers.DecimalField(
        required=False, max_digits=6, decimal_places=2, min_value=0
    )
    gpu_model = serializers.CharField(required=False, max_length=255)
    storage_total_gb = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0
    )

    # Operating system
    os_name = serializers.CharField(required=False, max_length=100)
    os_version = serializers.CharField(required=False, max_length=100)

    # Network
    ip_address = serializers.IPAddressField(required=False)
    mac_address = serializers.CharField(required=False, max_length=17)

    # Owner
    owner_id = serializers.IntegerField(required=False, help_text="Owner user ID")

    # Club linking via token
    club_token = serializers.CharField(
        required=False, allow_blank=True, max_length=8,
        help_text="8-char club token — auto-links this PC to the club",
    )
