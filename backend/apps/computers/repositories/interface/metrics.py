from datetime import datetime
from typing import Optional, Protocol

from django.db.models import QuerySet

from apps.computers.models import Computer, ComputerMetrics


class IComputerMetricsRepository(Protocol):
    """Interface for ComputerMetrics repository"""

    def get_all(self) -> QuerySet[ComputerMetrics]:
        """Get all metrics"""
        ...

    def get_by_id(self, metrics_id: int) -> Optional[ComputerMetrics]:
        """Get metrics by ID"""
        ...

    def get_by_computer(
        self,
        computer: Computer,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> QuerySet[ComputerMetrics]:
        """Get metrics for a computer, optionally filtered by date range"""
        ...

    def get_latest_by_computer(self, computer: Computer) -> Optional[ComputerMetrics]:
        """Get latest metrics for a computer"""
        ...

    def create(self, **data) -> ComputerMetrics:
        """Create new metrics entry"""
        ...

    def delete_old_metrics(self, days: int = 30) -> int:
        """Delete metrics older than specified days"""
        ...
