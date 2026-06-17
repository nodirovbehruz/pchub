from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.computers.api.v1.serializers.metrics import (
    ComputerMetricsCreateSerializer,
    ComputerMetricsSerializer,
)
from apps.computers.repositories.implementation.computer import ComputerRepository
from apps.computers.repositories.implementation.metrics import ComputerMetricsRepository
from apps.computers.services.implementation.metrics import ComputerMetricsService


@extend_schema(tags=["Computers - Metrics"])
class ComputerMetricsCreateAPIView(generics.CreateAPIView):
    """
    Record computer metrics from C# app

    POST endpoint for C# application to send CPU, RAM, and other metrics.
    Automatically updates computer status to ONLINE.

    Example C# request:
    ```json
    {
        "computer_id": 1,
        "cpu_usage": 45.5,
        "ram_used": 8.2,
        "ram_available": 7.8,
        "cpu_temperature": 65.0,
        "disk_used": 450.0,
        "disk_available": 550.0,
        "network_upload": 1.5,
        "network_download": 10.2
    }
    ```
    """

    serializer_class = ComputerMetricsCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    service = ComputerMetricsService(
        metrics_repository=ComputerMetricsRepository(),
        computer_repository=ComputerRepository(),
    )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Record metrics
        metrics = self.service.record_metrics(
            computer_id=serializer.validated_data["computer_id"],
            cpu_usage=serializer.validated_data["cpu_usage"],
            ram_used=serializer.validated_data["ram_used"],
            ram_available=serializer.validated_data["ram_available"],
            cpu_temperature=serializer.validated_data.get("cpu_temperature"),
            disk_used=serializer.validated_data.get("disk_used"),
            disk_available=serializer.validated_data.get("disk_available"),
            network_upload=serializer.validated_data.get("network_upload"),
            network_download=serializer.validated_data.get("network_download"),
        )

        # Return recorded metrics
        response_serializer = ComputerMetricsSerializer(metrics)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Computers - Metrics"],
    parameters=[
        OpenApiParameter(
            name="hours",
            description="Number of hours of history to retrieve (default: 24)",
            required=False,
            type=int,
        )
    ],
)
class ComputerMetricsHistoryAPIView(APIView):
    """
    Get metrics history for a computer

    Query parameters:
    - hours: Number of hours of history (default: 24)
    """

    permission_classes = [permissions.IsAuthenticated]
    service = ComputerMetricsService()

    def get(self, request, computer_id):
        try:
            hours = int(request.query_params.get("hours", 24))
        except (TypeError, ValueError):
            return Response({"error": "hours должен быть числом"}, status=status.HTTP_400_BAD_REQUEST)

        # SECURITY (IDOR): was keyed only by computer_id with no club check — any
        # authenticated user could read any club's PC metrics by iterating ids. Scope
        # to a club the caller belongs to.
        from apps.clubs.api.v1.mixins import validated_club_id
        from apps.computers.models import Computer
        cid = validated_club_id(request)
        if not cid or not Computer.objects.filter(id=computer_id, club_id=cid).exists():
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get metrics history
        data = self.service.get_computer_metrics_history(
            computer_id=computer_id, hours=hours
        )

        # Serialize data
        metrics_serializer = ComputerMetricsSerializer(
            data["metrics_history"], many=True
        )
        latest_serializer = ComputerMetricsSerializer(data["latest_metrics"])

        return Response(
            {
                "computer_id": computer_id,
                "computer_name": data["computer"].name,
                "hours": hours,
                "total_entries": data["total_entries"],
                "latest_metrics": latest_serializer.data,
                "history": metrics_serializer.data,
            }
        )
