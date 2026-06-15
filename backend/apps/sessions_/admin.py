from django.contrib import admin

from .models import AdminCall, ClientSession, Review, SessionHost


class SessionHostInline(admin.TabularInline):
    model = SessionHost
    extra = 0


@admin.register(ClientSession)
class ClientSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "club", "client", "tariff", "status", "duration_minutes", "started_at")
    list_filter = ("status", "club", "postpaid")
    search_fields = ("client__username", "client__phone")
    autocomplete_fields = ("club", "client", "tariff")
    raw_id_fields = ("payment", "shift")
    inlines = [SessionHostInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "club", "client", "rating", "tip_amount", "is_read", "created_at")
    list_filter = ("rating", "is_read", "club", "is_anonymous")
    search_fields = ("client__username", "comment")
    readonly_fields = ("created_at",)


@admin.register(AdminCall)
class AdminCallAdmin(admin.ModelAdmin):
    list_display = ("id", "club", "computer", "client", "called_at", "is_answered")
    list_filter = ("club",)
    readonly_fields = ("called_at",)
