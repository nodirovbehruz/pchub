from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ClubNetwork(models.Model):
    """Network of clubs owned by one user.

    SmartShell «Сеть клубов» — one network per owner. Enables:
    - shared client deposit transfers (Business)
    - shared maximum personal discount cap
    - main club designation
    - optional app sync (full / templates)
    """

    name = models.CharField(_("Name"), max_length=120)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_network",
    )

    main_club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="main_for_networks",
    )

    max_personal_discount = models.PositiveSmallIntegerField(
        default=100,
        help_text=_("Cap for personal discounts inside this network (0..100)"),
    )
    allow_deposit_transfer = models.BooleanField(default=True)
    sync_apps_from_main = models.BooleanField(
        default=False,
        help_text=_("Copy game/app cards from main_club to others"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "club_networks"
        verbose_name = _("Club Network")
        verbose_name_plural = _("Club Networks")
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
