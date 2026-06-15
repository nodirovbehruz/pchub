from django.db import models
from django.utils.translation import gettext_lazy as _


class PaymentMethod(models.TextChoices):
    CASH = "cash", _("Наличные")
    CARD = "card", _("Карта")
    TRANSFER = "transfer", _("Перевод")
