from django.contrib import admin

from apps.clubs.models import (
    ClientGroup,
    Club,
    ClubMembership,
    ClubNetwork,
    ClubSubscription,
    Notification,
    PromisedPayment,
    SubscriptionPlan,
    UserClubProfile,
)


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "owner", "network", "is_trial", "is_verified", "is_active", "created_at")
    list_filter = ("is_trial", "is_verified", "is_active", "city", "network")
    search_fields = ("name", "city", "owner__phone", "owner__username")
    autocomplete_fields = ("owner", "network")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "site", "owner", "network", "is_active")}),
        ("Address", {"fields": ("country", "city", "timezone", "street", "house")}),
        ("Contact", {"fields": ("contact_name", "contact_phone")}),
        ("Subscription", {"fields": ("is_trial", "trial_until", "is_verified")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ClubMembership)
class ClubMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("user__username", "user__phone", "club__name")
    autocomplete_fields = ("user", "club")
    readonly_fields = ("created_at",)


@admin.register(ClubNetwork)
class ClubNetworkAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "main_club", "max_personal_discount", "allow_deposit_transfer")
    search_fields = ("name", "owner__username")
    autocomplete_fields = ("owner", "main_club")


@admin.register(ClientGroup)
class ClientGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "percent_discount", "created_at")
    list_filter = ("club",)
    search_fields = ("name", "club__name")


@admin.register(UserClubProfile)
class UserClubProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "deposit_money", "bonus_balance", "personal_discount", "is_blocked", "last_visit_at")
    list_filter = ("club", "is_blocked")
    search_fields = ("user__username", "user__phone", "club__name")
    autocomplete_fields = ("user", "club", "group")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "club", "type", "title", "sent_at", "read_at")
    list_filter = ("type", "club")
    search_fields = ("title", "body", "user__username")
    readonly_fields = ("sent_at",)


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "tier", "monthly_price", "max_pcs", "is_active")
    list_filter = ("tier", "is_active")
    list_editable = ("is_active",)
    search_fields = ("name", "tier")


@admin.register(ClubSubscription)
class ClubSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("club", "plan", "status", "expires_at", "auto_renew")
    list_filter = ("status", "plan", "auto_renew")
    autocomplete_fields = ("club", "plan")


@admin.register(PromisedPayment)
class PromisedPaymentAdmin(admin.ModelAdmin):
    list_display = ("subscription", "fee_amount", "granted_at", "due_at", "paid_at")
    list_filter = ("subscription__club",)
    readonly_fields = ("granted_at",)
