from django.db import models
from django.utils.translation import gettext_lazy as _


class ComputerStatus(models.TextChoices):
    """Computer status choices"""

    ONLINE = "ONLINE", _("Online")
    OFFLINE = "OFFLINE", _("Offline")
    MAINTENANCE = "MAINTENANCE", _("Maintenance")
    DISABLED = "DISABLED", _("Disabled")
