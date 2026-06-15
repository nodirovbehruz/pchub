from django.db import models
from django.utils.translation import gettext_lazy as _


class SessionStatus(models.TextChoices):
    """Game session status choices"""

    ACTIVE = "ACTIVE", _("Active")
    PAUSED = "PAUSED", _("Paused")
    ENDED = "ENDED", _("Ended")
