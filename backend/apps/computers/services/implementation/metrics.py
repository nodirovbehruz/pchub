from datetime import timedelta
from typing import Any, Dict

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.computers.models import ComputerMetrics, ComputerStatus
from apps.computers.repositories.implementation.computer import ComputerRepository
from apps.computers.repositories.implementation.metrics import ComputerMetricsRepository
from apps.computers.repositories.interface.computer import IComputerRepository
from apps.computers.repositories.interface.metrics import IComputerMetricsRepository
from apps.computers.services.interface.metrics import IComputerMetricsService


class ComputerMetricsService(IComputerMetricsService):
    """Service for ComputerMetrics - handles C# app integration"""

    def __init__(
        self,
        metrics_repository: IComputerMetricsRepository = None,
        computer_repository: IComputerRepository = None,
    ):
        self.metrics_repository = metrics_repository or ComputerMetricsRepository()
        self.computer_repository = computer_repository or ComputerRepository()

    def record_metrics(
        self,
        computer_id: int,
        cpu_usage: float,
        ram_used: float,
        ram_available: float,
        cpu_temperature: float = None,
        disk_used: float = None,
        disk_available: float = None,
        network_upload: float = None,
        network_download: float = None,
    ) -> ComputerMetrics:
        """
        Record computer metrics from C# app
        Automatically calculates RAM usage percentage
        Updates computer status to ONLINE
        """
        # Get computer
        computer = self.computer_repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        # Validate metrics
        if cpu_usage < 0 or cpu_usage > 100:
            raise ValidationError({"cpu_usage": "CPU usage must be between 0 and 100"})

        if ram_used < 0 or ram_available < 0:
            raise ValidationError({"ram": "RAM values cannot be negative"})

        # Calculate RAM usage percentage
        total_ram = ram_used + ram_available
        ram_usage_percent = (ram_used / total_ram * 100) if total_ram > 0 else 0

        # Create metrics entry
        metrics = self.metrics_repository.create(
            computer=computer,
            cpu_usage_percent=cpu_usage,
            cpu_temperature=cpu_temperature,
            ram_used_gb=ram_used,
            ram_available_gb=ram_available,
            ram_usage_percent=ram_usage_percent,
            disk_used_gb=disk_used,
            disk_available_gb=disk_available,
            network_upload_mbps=network_upload,
            network_download_mbps=network_download,
        )

        # Update computer status to ONLINE
        computer.update_status(ComputerStatus.ONLINE)

        return metrics

    def get_computer_metrics_history(
        self, computer_id: int, hours: int = 24
    ) -> Dict[str, Any]:
        """Get metrics history for a computer"""
        # Get computer
        computer = self.computer_repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        # Get metrics from last N hours
        start_date = timezone.now() - timedelta(hours=hours)
        metrics = self.metrics_repository.get_by_computer(
            computer=computer, start_date=start_date
        )

        # Get latest metrics
        latest = self.metrics_repository.get_latest_by_computer(computer)

        return {
            "computer": computer,
            "metrics_history": metrics,
            "latest_metrics": latest,
            "hours": hours,
            "total_entries": metrics.count(),
        }
