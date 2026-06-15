from django.contrib import admin
from .models import Abonement, PurchasedAbonement

@admin.register(Abonement)
class AbonementAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price", "is_active", "start_time", "end_time")
    list_filter = ("is_active",)
    search_fields = ("name",)

@admin.register(PurchasedAbonement)
class PurchasedAbonementAdmin(admin.ModelAdmin):
    list_display = ("user", "abonement", "purchase_date", "is_used")
    list_filter = ("is_used", "purchase_date")
    search_fields = ("user__username", "abonement__name")
