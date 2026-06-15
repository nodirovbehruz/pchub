from django.contrib import admin

from .models import Achievement, CashbackRule, Discount, Promocode, UserAchievement


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "percent", "is_active", "created_at")
    list_filter = ("club", "is_active")
    search_fields = ("name",)
    list_editable = ("is_active",)


@admin.register(Promocode)
class PromocodeAdmin(admin.ModelAdmin):
    list_display = ("code", "club", "reward_type", "value", "usage_count", "usage_limit", "is_active")
    list_filter = ("club", "reward_type", "is_active")
    search_fields = ("code", "name")
    list_editable = ("is_active",)
    filter_horizontal = ("specific_clients",)


@admin.register(CashbackRule)
class CashbackRuleAdmin(admin.ModelAdmin):
    list_display = ("club", "deposit_threshold", "accrual_type", "value", "is_active")
    list_filter = ("club", "accrual_type", "is_active")
    list_editable = ("is_active",)


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "trigger_type", "threshold", "reward_type", "reward_value", "is_active")
    list_filter = ("club", "trigger_type", "reward_type", "is_active")
    search_fields = ("name", "description")


@admin.register(UserAchievement)
class UserAchievementAdmin(admin.ModelAdmin):
    list_display = ("user", "achievement", "unlocked_at")
    list_filter = ("achievement__club",)
    search_fields = ("user__username", "achievement__name")
    readonly_fields = ("unlocked_at",)
