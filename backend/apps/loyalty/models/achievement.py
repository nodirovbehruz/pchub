from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AchievementTrigger(models.TextChoices):
    REGISTRATION = "registration", _("On registration")
    TOPUP_SINGLE = "topup_single", _("Single topup ≥ threshold")
    TOPUP_TOTAL = "topup_total", _("Total topup ≥ threshold")
    SPEND_SINGLE = "spend_single", _("Single spend ≥ threshold")
    SPEND_TOTAL = "spend_total", _("Total spend ≥ threshold")
    HOURS_IN_CLUB = "hours_in_club", _("Total hours in club ≥ threshold")


class RewardType(models.TextChoices):
    NONE = "none", _("None")
    DISCOUNT = "discount", _("Personal discount %")
    BONUS = "bonus", _("Bonus deposit")


class Achievement(models.Model):
    """One-shot achievement triggered by client behaviour.

    SmartShell `/achievements`:
    - Award given only once per client.
    - Cannot be edited (recreate instead) — counting starts from creation.
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    icon = models.ImageField(upload_to="achievements/", blank=True, null=True)

    trigger_type = models.CharField(max_length=20, choices=AchievementTrigger.choices)
    threshold = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0"),
        help_text=_("Threshold value to unlock the achievement"),
    )

    reward_type = models.CharField(
        max_length=10, choices=RewardType.choices, default=RewardType.NONE,
    )
    reward_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"),
        help_text=_("Percent for DISCOUNT, money for BONUS, ignored for NONE"),
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "loyalty_achievements"
        verbose_name = _("Achievement")
        verbose_name_plural = _("Achievements")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} [{self.get_trigger_type_display()}]"


class UserAchievement(models.Model):
    """Records that a user has unlocked an achievement (one-time)."""

    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="unlocked_by",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "loyalty_user_achievements"
        verbose_name = _("User Achievement")
        verbose_name_plural = _("User Achievements")
        unique_together = [("achievement", "user")]
        ordering = ["-unlocked_at"]
