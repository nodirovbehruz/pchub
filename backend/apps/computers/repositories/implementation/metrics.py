from datetime import datetime, timedelta
from typing import Optional

from django.db.models import QuerySet
from django.utils import timezone

from apps.computers.models import Computer, ComputerMetrics
from apps.computers.repositories.interface.metrics import IComputerMetricsRepository


class ComputerMetricsRepository(IComputerMetricsRepository):
    """Repository for ComputerMetrics model"""

    def __init__(self):
        self.model = ComputerMetrics

    def get_all(self) -> QuerySet[ComputerMetrics]:
        """Get all metrics"""
        return self.model.objects.select_related("computer").all()

    def get_by_id(self, metrics_id: int) -> Optional[ComputerMetrics]:
        """Get metrics by ID"""
        try:
            return self.model.objects.select_related("computer").get(id=metrics_id)
        except self.model.DoesNotExist:
            return None

    def get_by_computer(
        self,
        computer: Computer,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> QuerySet[ComputerMetrics]:
        """Get metrics for a computer, optionally filtered by date range"""
        queryset = self.model.objects.filter(computer=computer)

        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)

        return queryset.order_by("-timestamp")

    def get_latest_by_computer(self, computer: Computer) -> Optional[ComputerMetrics]:
        """Get latest metrics for a computer"""
        return (
            self.model.objects.filter(computer=computer).order_by("-timestamp").first()
        )

    def create(self, **data) -> ComputerMetrics:
        """Create new metrics entry"""
        return self.model.objects.create(**data)

    def delete_old_metrics(self, days: int = 30) -> int:
        """Delete metrics older than specified days"""
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = self.model.objects.filter(timestamp__lt=cutoff_date).delete()
        return deleted_count
