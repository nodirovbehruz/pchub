from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Review(models.Model):
    """Client review after a session.

    SmartShell: modal after session end — rating 1–5, comment, optional contact,
    optional tip. Anonymous reviews allowed.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviews",
    )
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviews",
    )
    shift = models.ForeignKey(
        "billing.Shift",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviews",
    )
    session = models.ForeignKey(
        "club_sessions.ClientSession",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField()  # 1..5
    comment = models.TextField(blank=True, default="")
    contact_info = models.CharField(max_length=255, blank=True, default="")
    tip_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text=_("Tip charged from client's real deposit (not bonus)"),
    )
    tip_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="received_tips",
        help_text=_("Admin who was on shift when tip was given"),
    )

    is_anonymous = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["club", "-created_at"]),
            models.Index(fields=["is_read"]),
        ]

    def __str__(self):
        return f"Review #{self.id} {self.rating}★ — {self.club}"
