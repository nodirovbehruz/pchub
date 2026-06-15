from django.db import models
from django.utils import timezone

class Abonement(models.Model):
    name = models.CharField("Название", max_length=100)
    duration_minutes = models.PositiveIntegerField("Длительность (мин)")
    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    is_active = models.BooleanField("Активен", default=True)
    
    # SENET feature: Fixed time slots (e.g. Night starts at 22:00)
    start_time = models.TimeField("Время начала доступности", null=True, blank=True)
    end_time = models.TimeField("Время окончания доступности", null=True, blank=True)

    class Meta:
        verbose_name = "Абонемент"
        verbose_name_plural = "Абонементы"

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} мин) - {self.price} руб."

class PurchasedAbonement(models.Model):
    user = models.ForeignKey("accounts.CustomUser", on_delete=models.CASCADE, related_name="purchased_abonements")
    abonement = models.ForeignKey(Abonement, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.abonement.name}"
