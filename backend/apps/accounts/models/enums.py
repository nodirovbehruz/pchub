from django.db import models
from django.utils.translation import gettext_lazy as _


class UserType(models.TextChoices):
    """User type choices"""

    OWNER = "owner", _("Владелец")
    MANAGER = "manager", _("Менеджер")
    OPERATOR = "operator", _("Оператор")
    ADMIN = "admin", _("Администратор")
    USER = "user", _("Пользователь")
