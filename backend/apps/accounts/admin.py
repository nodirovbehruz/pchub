from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django.urls import path
from django.shortcuts import render, redirect
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.contrib import messages

from .models import CustomUser
from apps.billing.models.balance import UserBalance
from apps.billing.models.payment import Payment


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Custom user admin with refined icon sizing for visual consistency."""

    list_display = [
        "username",
        "email",
        "phone",
        "full_name",
        "user_type_badge",
        "is_active_status",
        "is_verified_status",
        "is_active_session_status",
        "created_at",
    ]

    list_filter = [
        "user_type",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_active_session",
        "email_verified",
        "phone_verified",
        "region",
        "language",
        "created_at",
        "last_login",
    ]

    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
    ]

    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    # --- FIELDSETS ---
    fieldsets = (
        (None, {"fields": ("id", "username", "password")}),
        (
            _("Contact & Verification"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "email_verified",
                    "phone",
                    "phone_verified",
                    ("profile_image", "profile_image_preview"),
                )
            },
        ),
        (
            _("Permissions & Role"),
            {
                "fields": (
                    "user_type",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Geodata & Preferences"),
            {
                "fields": ("region", "language"),
            },
        ),
        (
            _("Session & Timestamps"),
            {
                "fields": (
                    "is_active_session",
                    "last_login",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",  # First password input
                    "password2",  # Password confirmation input
                ),
            },
        ),
    )

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "last_login",
        "is_active_session",
        "profile_image_preview",
    ]

    # --- Custom display methods ---
    @admin.display(description="Image Preview")
    def profile_image_preview(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 150px;" />',
                obj.profile_image.url,
            )
        return "No Image"

    @admin.display(description="Full Name")
    def full_name(self, obj):
        """Display user's full name"""
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name if name else obj.get_username()

    # Consistent icon for the default 'is_active' field
    @admin.display(description="Active")
    def is_active_status(self, obj):
        """Standardized display for the is_active boolean field."""
        if obj.is_active:
            # Consistent Success color: Turquoise/Green
            return format_html(
                '<i class="fas fa-check-circle" style="color: #00FF00; font-size: 1.2rem;"></i>'
            )
        # Consistent Failure color: Red
        return format_html(
            '<i class="fas fa-times-circle" style="color: #FF0000; font-size: 1.2rem;"></i>'
        )

    @admin.display(description="Verified")
    def is_verified_status(self, obj):
        """Is verified status"""
        icon_size = "1.2rem"

        if obj.email_verified and obj.phone_verified:
            icon = "check-circle"
            color = "#00cba9"  # Turquoise (Success)
            title = "Email & Phone Verified"
        elif obj.email_verified or obj.phone_verified:
            icon = "exclamation-triangle"  # Changed to a warning triangle for partial verification
            color = "#ffc107"  # Yellow (Partial)
            title = "Partially Verified"
        else:
            icon = "times-circle"
            color = "#dc3545"  # Red (Failure)
            title = "Not Verified"

        return format_html(
            '<i class="fas fa-{}" title="{}" style="color: {}; font-size: {};"></i>',
            icon,
            title,
            color,
            icon_size,
        )

    @admin.display(description="Session")
    def is_active_session_status(self, obj):
        """
        Display active session status using a simplified, consistent icon,
        matching the appearance in the uploaded screenshot (toggle/slider style).
        """
        icon_size = "1.2rem"
        if obj.is_active_session:
            # Using the toggle icon for the Active Session indicator
            return format_html(
                '<i class="fas fa-toggle-on" title="Session Active" style="color: #00cba9; font-size: {};"></i>',
                icon_size,
            )
        return format_html(
            '<i class="fas fa-toggle-off" title="Session Inactive" style="color: #6c757d; font-size: {};"></i>',
            icon_size,
        )

    @admin.display(description="User Type")
    def user_type_badge(self, obj):
        """Display user type with colored badge (kept consistent)."""
        colors = {
            "admin": "#CB3CFF50",
            "user": "#2FFFF450",
        }
        color = colors.get(obj.user_type, "#6c757d")

        if obj.user_type == "admin":
            style_attr = f"background-color: {color}; color: black;"
        else:
            style_attr = f"background-color: {color}; color: white;"

        return format_html(
            '<span style="{} padding: 3px 10px; '
            'border-radius: 3px; width: 125px; border: 1px solid white; color: white; font-size: 11px; font-weight: bold; min-width: 60px; text-align: center; display: inline-block;">{}</span>',
            style_attr,
            obj.get_user_type_display().upper(),
        )

    # --- Custom actions ---
    @admin.action(description="Mark selected users as active")
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} user(s) successfully activated.")

    @admin.action(description="Mark selected users as inactive")
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} user(s) successfully deactivated.")

    @admin.action(description="Promote to admin")
    def promote_to_admin(self, request, queryset):
        updated = queryset.update(user_type="admin", is_staff=True)
        self.message_user(request, f"{updated} user(s) promoted to admin.")

    @admin.action(description="Demote to regular user")
    def demote_to_user(self, request, queryset):
        updated = queryset.update(user_type="user", is_staff=False)
        self.message_user(request, f"{updated} user(s) demoted to regular user.")

    @admin.action(description="End active sessions")
    def end_sessions(self, request, queryset):
        updated = queryset.filter(is_active_session=True).update(
            is_active_session=False
        )
        self.message_user(request, f"Ended sessions for {updated} user(s).")

    actions = [
        make_active,
        make_inactive,
        promote_to_admin,
        demote_to_user,
        end_sessions,
    ]

    # Customize form behavior
    def get_form(self, request, obj=None, **kwargs):
        """Customize form based on user permissions"""
        form = super().get_form(request, obj, **kwargs)

        # Only superusers can change superuser status
        if not request.user.is_superuser:
            if "is_superuser" in form.base_fields:
                form.base_fields["is_superuser"].disabled = True

        return form

    # --- SPRINT 4: CRM VIEW & TOPUP ────────────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('topup/', self.admin_site.admin_view(self.topup_view), name='crm_topup'),
        ]
        return custom_urls + urls

    def topup_view(self, request):
        """Handles balance top-up from the CRM modal"""
        if request.method == "POST":
            user_id = request.POST.get("user_id")
            minutes = int(request.POST.get("minutes", 0))
            amount_paid = float(request.POST.get("amount_paid", 0.0))
            payment_method = request.POST.get("payment_method", "cash")
            note = request.POST.get("note", "")
            next_url = request.POST.get("next", "..")

            user = CustomUser.objects.filter(id=user_id).first()
            if user and minutes > 0:
                # 1. Update balance
                balance, _ = UserBalance.objects.get_or_create(user=user)
                balance.add_minutes(minutes)

                # 2. Record payment
                Payment.objects.create(
                    user=user,
                    admin=request.user,
                    amount_paid=amount_paid,
                    minutes_added=minutes,
                    payment_method=payment_method,
                    note=note
                )
                messages.success(request, f"Баланс пользователя {user.username} успешно пополнен на {minutes} минут.")
            else:
                messages.error(request, "Ошибка: неверные данные для пополнения.")

            return redirect(next_url)
        return redirect("..")

    def changelist_view(self, request, extra_context=None):
        """Override default admin list with our SENET CRM view."""
        search_query = request.GET.get('q', '').strip()

        # Query all users
        users = CustomUser.objects.select_related('balance').all().order_by('-created_at')

        # Apply search
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone__icontains=search_query)
            )

        # Pagination (20 per page)
        paginator = Paginator(users, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Summary Stats
        total_users = CustomUser.objects.count()
        active_sessions = CustomUser.objects.filter(is_active_session=True).count()
        
        # Calculate zero balance and total time efficiently
        # Since UserBalance might not exist for some, we count those without balance or with 0 minutes
        balances = UserBalance.objects.all()
        users_with_balance_count = balances.count()
        zero_balance = (total_users - users_with_balance_count) + balances.filter(minutes_remaining=0).count()
        
        total_minutes = balances.aggregate(Sum('minutes_remaining'))['minutes_remaining__sum'] or 0
        total_minutes_h = round(total_minutes / 60, 1)

        # Need a plain list of users for the topup modal select dropdown
        all_users = CustomUser.objects.all().order_by('username')

        context = {
            # Provide standard admin context so it doesn't crash headers
            **(extra_context or {}),
            **self.admin_site.each_context(request),
            'title': _("CRM Пользователей"),
            'app_label': self.model._meta.app_label,
            
            # CRM Context
            'users': page_obj.object_list,
            'page_obj': page_obj,
            'search_query': search_query,
            'total_users': total_users,
            'active_sessions': active_sessions,
            'zero_balance': zero_balance,
            'total_minutes_h': total_minutes_h,
            'all_users': all_users,
        }
        return render(request, "admin/accounts/crm_users.html", context)
