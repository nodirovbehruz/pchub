from rest_framework import serializers

from apps.computers.models import ComputerMetrics


class ComputerMetricsSerializer(serializers.ModelSerializer):
    """Serializer for reading computer metrics data"""

    computer_name = serializers.CharField(source="computer.name", read_only=True)
    cpu_status = serializers.CharField(read_only=True)
    ram_status = serializers.CharField(read_only=True)

    class Meta:
        model = ComputerMetrics
        fields = [
            "id",
            "computer_name",
            "cpu_usage_percent",
            "cpu_temperature",
            "cpu_status",
            "ram_used_gb",
            "ram_available_gb",
            "ram_usage_percent",
            "ram_status",
            "disk_used_gb",
            "disk_available_gb",
            "network_upload_mbps",
            "network_download_mbps",
            "timestamp",
        ]
        read_only_fields = fields


class ComputerMetricsCreateSerializer(serializers.Serializer):
    """
    Serializer for C# app to send computer metrics
    Simple JSON format for easy C# integration
    """

    computer_id = serializers.IntegerField(
        required=True, help_text="ID of the computer"
    )

    # Required CPU metrics
    cpu_usage = serializers.FloatField(
        required=True,
        min_value=0,
        max_value=100,
        help_text="CPU usage percentage (0-100)",
    )

    # Required RAM metrics
    ram_used = serializers.FloatField(
        required=True, min_value=0, help_text="RAM used in GB"
    )
    ram_available = serializers.FloatField(
        required=True, min_value=0, help_text="RAM available in GB"
    )

    # Optional metrics
    cpu_temperature = serializers.FloatField(
        required=False, allow_null=True, help_text="CPU temperature in Celsius"
    )
    disk_used = serializers.FloatField(
        required=False, allow_null=True, min_value=0, help_text="Disk space used in GB"
    )
    disk_available = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Disk space available in GB",
    )
    network_upload = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Network upload speed in Mbps",
    )
    network_download = serializers.FloatField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Network download speed in Mbps",
    )
