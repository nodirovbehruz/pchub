from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AdminCall(models.Model):
    """Client pressed «Позвать админа» button in Shell.

    Rate-limited to 1 per minute per client at API layer.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="admin_calls",
    )
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="admin_calls",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="admin_calls",
        help_text=_("Null if Shell session was unauthenticated"),
    )
    shift = models.ForeignKey(
        "billing.Shift",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="admin_calls",
    )
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="answered_admin_calls",
    )

    called_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "admin_calls"
        verbose_name = _("Admin Call")
        verbose_name_plural = _("Admin Calls")
        ordering = ["-called_at"]

    def __str__(self):
        return f"AdminCall #{self.id} at {self.called_at:%H:%M}"

    @property
    def is_answered(self):
        return self.answered_at is not None
