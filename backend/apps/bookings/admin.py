from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "club", "client", "guest_name", "from_at", "to_at", "status")
    list_filter = ("status", "club")
    search_fields = ("client__username", "client__phone", "guest_name", "guest_phone", "comment")
    autocomplete_fields = ("club", "client", "created_by")
    filter_horizontal = ("hosts",)
    readonly_fields = ("created_at", "updated_at")
