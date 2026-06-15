from django.contrib import admin

from .models import BlockedApp, Integration, ShellSecurity, ShellTheme


@admin.register(ShellTheme)
class ShellThemeAdmin(admin.ModelAdmin):
    list_display = ("club", "primary_color", "splash_type", "splash_enabled", "updated_at")
    list_filter = ("splash_type", "splash_enabled")


class BlockedAppInline(admin.TabularInline):
    model = BlockedApp
    extra = 0


@admin.register(ShellSecurity)
class ShellSecurityAdmin(admin.ModelAdmin):
    list_display = ("club", "tightvnc_enabled", "block_external_storage", "block_chrome_downloads", "updated_at")
    list_filter = ("tightvnc_enabled", "block_external_storage", "block_chrome_downloads")
    inlines = [BlockedAppInline]


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ("club", "type", "is_active", "last_test_ok", "updated_at")
    list_filter = ("type", "is_active")
    list_editable = ("is_active",)
