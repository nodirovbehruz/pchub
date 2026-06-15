from typing import Any, Dict, Protocol

from apps.computers.models import ComputerMetrics


class IComputerMetricsService(Protocol):
    """Interface for ComputerMetrics service - handles C# app integration"""

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
        ...

    def get_computer_metrics_history(
        self, computer_id: int, hours: int = 24
    ) -> Dict[str, Any]:
        """Get metrics history for a computer"""
        ...
