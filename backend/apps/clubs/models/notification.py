from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    class Type(models.TextChoices):
        ADMIN_CALL = "admin_call", _("Admin call from client")
        SALE = "sale", _("Sale notification")
        BOOKING = "booking", _("Booking notification")
        STOCK_LOW = "stock_low", _("Stock low warning")
        SESSION = "session", _("Session event")
        SYSTEM = "system", _("System")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="notifications",
    )

    type = models.CharField(max_length=20, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=200, blank=True, default="")
    body = models.TextField(blank=True, default="")

    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "notifications"
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["user", "-sent_at"]),
            models.Index(fields=["club", "-sent_at"]),
        ]

    def __str__(self):
        return f"[{self.type}] {self.title or self.body[:40]}"
