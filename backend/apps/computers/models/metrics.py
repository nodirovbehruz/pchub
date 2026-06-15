from django.db import models
from django.utils.translation import gettext_lazy as _


class ComputerMetrics(models.Model):
    """
    Time-series metrics data for computers (CPU, RAM, etc.)
    Sent by C# application
    """

    # Relationship
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.CASCADE,
        related_name="metrics",
        help_text=_("Computer"),
    )

    # CPU Metrics
    cpu_usage_percent = models.DecimalField(
        max_digits=5, decimal_places=2, help_text=_("CPU usage percentage (0-100)")
    )
    cpu_temperature = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("CPU temperature in Celsius"),
    )

    # RAM Metrics
    ram_used_gb = models.DecimalField(
        max_digits=6, decimal_places=2, help_text=_("RAM used in GB")
    )
    ram_available_gb = models.DecimalField(
        max_digits=6, decimal_places=2, help_text=_("RAM available in GB")
    )
    ram_usage_percent = models.DecimalField(
        max_digits=5, decimal_places=2, help_text=_("RAM usage percentage (0-100)")
    )

    # Disk Metrics (Optional)
    disk_used_gb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Disk space used in GB"),
    )
    disk_available_gb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Disk space available in GB"),
    )

    # Network Metrics (Optional)
    network_upload_mbps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Network upload speed in Mbps"),
    )
    network_download_mbps = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Network download speed in Mbps"),
    )

    # Timestamp
    timestamp = models.DateTimeField(
        auto_now_add=True, help_text=_("When metrics were recorded")
    )

    class Meta:
        db_table = "computer_metrics"
        verbose_name = _("Computer Metrics")
        verbose_name_plural = _("Computer Metrics")
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["computer", "-timestamp"]),
            models.Index(fields=["-timestamp"]),
        ]

    def __str__(self):
        return f"{self.computer.name} - {self.timestamp}"

    @property
    def cpu_status(self):
        """Get CPU status based on usage"""
        if self.cpu_usage_percent is None:
            return "unknown"
        if self.cpu_usage_percent >= 90:
            return "critical"
        elif self.cpu_usage_percent >= 70:
            return "high"
        elif self.cpu_usage_percent >= 50:
            return "medium"
        return "low"

    @property
    def ram_status(self):
        """Get RAM status based on usage"""
        if self.ram_usage_percent is None:
            return "unknown"
        if self.ram_usage_percent >= 90:
            return "critical"
        elif self.ram_usage_percent >= 70:
            return "high"
        elif self.ram_usage_percent >= 50:
            return "medium"
        return "low"
