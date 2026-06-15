from django.db import models
from django.utils.translation import gettext_lazy as _


class ClientGroup(models.Model):
    """Group of clients within a club with a shared base discount.

    SmartShell: 'Группы клиентов' — name 2–16 chars, percent_discount 0..100.
    A client can be in only one group per club.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="client_groups",
    )
    name = models.CharField(_("Name"), max_length=16)
    percent_discount = models.PositiveSmallIntegerField(
        _("Discount %"),
        default=0,
        help_text=_("0..100, applied as a fallback when client has no personal discount"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "client_groups"
        verbose_name = _("Client Group")
        verbose_name_plural = _("Client Groups")
        unique_together = [("club", "name")]
        ordering = ["club_id", "name"]

    def __str__(self):
        return f"{self.name} ({self.club.name})"
