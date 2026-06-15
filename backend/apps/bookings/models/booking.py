from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class BookingStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    FINISHED = "finished", _("Finished")
    CANCELED = "canceled", _("Canceled")
    REDEEMED = "redeemed", _("Redeemed")  # клиент пришёл, сеанс начат


class Booking(models.Model):
    """Reservation of one or more PCs for a client at a given time window.

    SmartShell:
    - One booking can include several hosts (`hosts: [Int!]`).
    - Client may be null (guest booking with extra_info).
    - When booking time arrives, FIXED/PER_MINUTE sessions of the current PC
      auto-finish to free the slot.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    hosts = models.ManyToManyField(
        "computers.Computer",
        related_name="bookings",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="bookings",
    )
    # Guest info (when client is null)
    guest_name = models.CharField(max_length=120, blank=True, default="")
    guest_phone = models.CharField(max_length=32, blank=True, default="")

    from_at = models.DateTimeField(_("Booked from"))
    to_at = models.DateTimeField(_("Booked to"))

    status = models.CharField(
        max_length=12,
        choices=BookingStatus.choices,
        default=BookingStatus.ACTIVE,
    )
    comment = models.TextField(blank=True, default="")
    hard_booking = models.BooleanField(
        default=False,
        help_text=_("Hard booking: cannot start a session crossing this window"),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_bookings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bookings"
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")
        ordering = ["-from_at"]
        indexes = [
            models.Index(fields=["club", "from_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        who = self.client or (self.guest_name or "guest")
        return f"Booking #{self.id} — {who} {self.from_at:%Y-%m-%d %H:%M}"

    @property
    def starts_in_minutes(self):
        from django.utils import timezone
        if self.status != BookingStatus.ACTIVE:
            return 0
        delta = self.from_at - timezone.now()
        return max(0, int(delta.total_seconds() // 60))
