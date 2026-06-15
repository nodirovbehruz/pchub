import secrets
import string

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def _generate_club_token():
    """Generate a unique 8-char uppercase alphanumeric token (e.g. K7X2M9QA)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


class Club(models.Model):
    name = models.CharField(_("Club name"), max_length=120)
    site = models.URLField(_("Site or social"), blank=True, default="")

    country = models.CharField(_("Country"), max_length=64, blank=True, default="")
    city = models.CharField(_("City"), max_length=64, blank=True, default="")
    timezone = models.CharField(_("Timezone"), max_length=64, default="Asia/Tashkent")
    street = models.CharField(_("Street"), max_length=120, blank=True, default="")
    house = models.CharField(_("House"), max_length=20, blank=True, default="")

    contact_name = models.CharField(_("Contact name"), max_length=120, blank=True, default="")
    contact_phone = models.CharField(_("Contact phone"), max_length=32, blank=True, default="")

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_clubs",
        verbose_name=_("Owner"),
    )

    network = models.ForeignKey(
        "clubs.ClubNetwork",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="clubs",
    )

    club_token = models.CharField(
        _("Club token"),
        max_length=8,
        unique=True,
        blank=True,
        help_text=_("8-char code printed on the shell setup screen so PC auto-links to this club"),
    )

    is_trial = models.BooleanField(_("Trial"), default=True)
    trial_until = models.DateTimeField(_("Trial ends at"), null=True, blank=True)
    is_verified = models.BooleanField(
        _("Verified"), default=False,
        help_text=_("Required for online payments and SmartGamer search"),
    )
    is_active = models.BooleanField(_("Active"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Club")
        verbose_name_plural = _("Clubs")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.club_token:
            # Generate unique token, retry if collision
            token = _generate_club_token()
            while Club.objects.filter(club_token=token).exists():
                token = _generate_club_token()
            self.club_token = token
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def address(self):
        parts = [p for p in [self.city, self.street, self.house] if p]
        return ", ".join(parts)


class ClubMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        MANAGER = "manager", _("Manager")
        OPERATOR = "operator", _("Operator")
        ACCOUNTANT = "accountant", _("Accountant")
        SYSADMIN = "sysadmin", _("SysAdmin")
        MARKETER = "marketer", _("Marketer")
        OTHER = "other", _("Other")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=Role.choices,
        default=Role.OPERATOR,
    )
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Club Membership")
        verbose_name_plural = _("Club Memberships")
        unique_together = [("user", "club")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} @ {self.club} ({self.role})"
