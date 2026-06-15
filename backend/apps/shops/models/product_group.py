from django.db import models
from django.utils.translation import gettext_lazy as _


class ProductGroup(models.Model):
    """Group of products with schedule controlling availability/visibility.

    SmartShell «Группа товаров»: name + schedule (days of week + time window).
    Used as soft-grouping in Shop UI (separate from Product.category).
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="product_groups",
    )
    name = models.CharField(_("Name"), max_length=50)

    # Schedule
    schedule_days = models.CharField(
        max_length=7, default="1234567",
        help_text=_("Days when group is visible/sellable. 1=Mon..7=Sun"),
    )
    schedule_start = models.TimeField(null=True, blank=True)
    schedule_end = models.TimeField(null=True, blank=True)

    show_in_shell = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shop_product_groups"
        verbose_name = _("Product Group")
        verbose_name_plural = _("Product Groups")
        ordering = ["club_id", "name"]
        unique_together = [("club", "name")]

    def __str__(self):
        return f"{self.name} ({self.club.name})"
