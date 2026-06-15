from django.db import models
from django.utils.translation import gettext_lazy as _


class ComputerGroup(models.Model):
    """A zone of PCs inside a club (e.g. Main Zone, VIP Lounge).

    Used for visual map zoning, per-zone tariff pricing and bulk operations.
    """

    name = models.CharField(_("Name"), max_length=80)
    slug = models.SlugField(_("Slug"), max_length=80, blank=True, default="")

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="computer_groups",
        verbose_name=_("Club"),
    )

    color = models.CharField(
        _("Color"),
        max_length=20,
        default="#6366f1",
        help_text=_("Display color of the zone in the UI"),
    )
    position = models.IntegerField(
        _("Position"),
        default=0,
        help_text=_("Sort order on the map"),
    )

    is_active = models.BooleanField(_("Active"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "computer_groups"
        verbose_name = _("Computer Group")
        verbose_name_plural = _("Computer Groups")
        ordering = ["club_id", "position", "name"]
        unique_together = [("club", "name")]

    def __str__(self):
        return f"{self.name} ({self.club.name})"

    @property
    def computers_count(self):
        return self.computers.filter(is_active=True).count()
