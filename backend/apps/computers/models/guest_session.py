from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class GuestSession(models.Model):
    """
    Tracks sessions opened manually by admin (without a user account).
    Useful for 'pay-after-play' scenarios.
    """
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.CASCADE,
        related_name="guest_sessions",
    )
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Billing info
    rate_per_hour = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text=_("Current hourly rate for this computer")
    )
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text=_("Calculated amount at end of session")
    )
    
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "guest_sessions"
        verbose_name = _("Guest Session")
        verbose_name_plural = _("Guest Sessions")
        ordering = ["-start_time"]

    def __str__(self):
        status = "Active" if self.is_active else "Ended"
        return f"Guest on {self.computer.pc_number} ({status})"

    def calculate_cost(self):
        """Calculates cost based on time played and hourly rate"""
        if not self.end_time and self.is_active:
            end = timezone.now()
        else:
            end = self.end_time or timezone.now()
            
        duration = end - self.start_time
        hours = duration.total_seconds() / 3600.0
        return round(float(self.rate_per_hour) * hours, 2)
