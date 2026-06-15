from decimal import Decimal

from django import forms
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from apps.games.models import Game

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    Abonement, AnalyticsMetrics, CashOrder, OperationLog,
    Payment, PaymentMethod, PurchasedAbonement,
    TariffPlan, TariffPrice, UserBalance,
)


@admin.register(CashOrder)
class CashOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "amount", "club", "shift", "admin", "created_at")
    list_filter = ("type", "club")
    search_fields = ("comment",)
    readonly_fields = ("created_at",)


@admin.register(OperationLog)
class OperationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "subject", "action", "object_repr", "club")
    list_filter = ("action", "club")
    search_fields = ("object_repr", "object_id")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
from .services.implementation.billing import BillingService

_service = BillingService()
User = get_user_model()


# ── Top-Up form (user-based) ─────────────────────────────────────────────────


class UserTopUpForm(forms.Form):
    minutes = forms.IntegerField(
        min_value=1,
        max_value=1440,
        label="Время (минуты)",
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": 1, "max": 1440}
        ),
    )
    amount_paid = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label="Сумма оплаты",
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    payment_method = forms.ChoiceField(
        choices=[
            (PaymentMethod.CASH, "Наличные 💵"),
            (PaymentMethod.CARD, "Карта 💳"),
            (PaymentMethod.TRANSFER, "Перевод 📱"),
        ],
        label="Способ оплаты",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    note = forms.CharField(
        required=False,
        label="Примечание",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )


# ── UserBalance Admin ─────────────────────────────────────────────────────────


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        # Hide from sidebar and app index (redundant with CRM Users list)
        return False

    list_display = [
        "user_link",
        "balance_badge",
        "status_badge",
        "total_paid_display",
        "last_updated",
        "topup_button",
    ]
    list_filter = ["is_active"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = [
        "user",
        "minutes_remaining",
        "formatted_time",
        "hours_remaining",
        "is_active",
        "last_updated",
        "created_at",
    ]
    ordering = ["user__username"]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:balance_id>/topup/",
                self.admin_site.admin_view(self.topup_view),
                name="billing_user_topup",
            ),
        ]
        return custom + urls

    def topup_view(self, request, balance_id):
        balance = get_object_or_404(UserBalance, pk=balance_id)
        user = balance.user

        if request.method == "POST":
            form = UserTopUpForm(request.POST)
            if form.is_valid():
                result = _service.topup_user(
                    user_id=str(user.pk),
                    minutes=form.cleaned_data["minutes"],
                    amount_paid=form.cleaned_data["amount_paid"],
                    payment_method=form.cleaned_data["payment_method"],
                    admin=request.user,
                    note=form.cleaned_data.get("note", ""),
                )
                messages.success(
                    request,
                    f"✅ {user.username}: добавлено {result['minutes_added']} мин. "
                    f"Остаток: {result['formatted_time']}",
                )
                return HttpResponseRedirect(
                    reverse("admin:billing_userbalance_change", args=[balance_id])
                )
        else:
            form = UserTopUpForm(initial={"minutes": 60, "amount_paid": "0.00"})

        tariffs = TariffPlan.objects.filter(is_active=True).order_by("price")
        context = {
            **self.admin_site.each_context(request),
            "title": f"Пополнить баланс — {user.username}",
            "form": form,
            "balance": balance,
            "user_obj": user,
            "opts": self.model._meta,
            "tariffs": tariffs,
            "presets": [
                ("30 мин", 30),
                ("1 час", 60),
                ("1.5 ч", 90),
                ("2 ч", 120),
                ("3 ч", 180),
                ("4 ч", 240),
                ("5 ч", 300),
                ("6 ч", 360),
            ],
        }
        return render(request, "admin/billing/topup_form.html", context)

    actions = [
        "add_30_min",
        "add_60_min",
        "add_120_min",
        "add_240_min",
        "reset_balance",
        "deactivate",
    ]

    @admin.action(description="⏱ Добавить 30 минут (бесплатно)")
    def add_30_min(self, request, queryset):
        self._bulk_add(request, queryset, 30)

    @admin.action(description="⏱ Добавить 1 час (бесплатно)")
    def add_60_min(self, request, queryset):
        self._bulk_add(request, queryset, 60)

    @admin.action(description="⏱ Добавить 2 часа (бесплатно)")
    def add_120_min(self, request, queryset):
        self._bulk_add(request, queryset, 120)

    @admin.action(description="⏱ Добавить 4 часа (бесплатно)")
    def add_240_min(self, request, queryset):
        self._bulk_add(request, queryset, 240)

    @admin.action(description="🔴 Обнулить баланс (отозвать доступ немедленно)")
    def reset_balance(self, request, queryset):
        count = 0
        for bal in queryset:
            bal.minutes_remaining = 0
            bal.is_active = False
            bal.save(update_fields=["minutes_remaining", "is_active", "last_updated"])
            count += 1
        self.message_user(
            request, f"Баланс обнулён для {count} пользователей.", messages.ERROR
        )

    @admin.action(description="🚫 Отозвать доступ (без обнуления баланса)")
    def deactivate(self, request, queryset):
        count = 0
        for bal in queryset:
            bal.is_active = False
            bal.save(update_fields=["is_active", "last_updated"])
            count += 1
        self.message_user(
            request, f"Доступ отозван для {count} пользователей.", messages.WARNING
        )

    def _bulk_add(self, request, queryset, minutes):
        count = 0
        for bal in queryset:
            _service.topup_user(
                user_id=str(bal.user_id),
                minutes=minutes,
                amount_paid=Decimal("0"),
                payment_method=PaymentMethod.CASH,
                admin=request.user,
                note=f"Bulk action: +{minutes} min",
            )
            count += 1
        self.message_user(
            request,
            f"+{minutes} мин. добавлено для {count} пользователей.",
            messages.SUCCESS,
        )

    @admin.display(description="Пользователь", ordering="user__username")
    def user_link(self, obj):
        url = reverse("admin:accounts_customuser_change", args=[obj.user_id])
        return format_html(
            '<a href="{}" style="font-weight:600">{}</a>', url, obj.user.username
        )

    @admin.display(description="Остаток", ordering="minutes_remaining")
    def balance_badge(self, obj):
        if obj.minutes_remaining == 0:
            color, bg = "#fff", "#dc3545"
        elif obj.minutes_remaining <= 10:
            color, bg = "#000", "#ffc107"
        else:
            color, bg = "#fff", "#198754"
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;font-weight:700;font-size:13px">{}</span>',
            bg,
            color,
            obj.formatted_time,
        )

    @admin.display(description="Статус", ordering="is_active")
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background:#198754;color:#fff;padding:2px 8px;border-radius:10px">🟢 Активен</span>'
            )
        return format_html(
            '<span style="background:#6c757d;color:#fff;padding:2px 8px;border-radius:10px">⭕ Неактивен</span>'
        )

    @admin.display(description="Всего оплачено")
    def total_paid_display(self, obj):
        total = (
            Payment.objects.filter(user=obj.user).aggregate(t=Sum("amount_paid"))["t"]
            or 0
        )
        return format_html(
            '<span style="color:#0dcaf0;font-weight:600">{}</span>', f"{total:,.2f}"
        )

    @admin.display(description="Пополнить")
    def topup_button(self, obj):
        url = reverse("admin:billing_user_topup", args=[obj.pk])
        return format_html(
            '<a href="{}" class="btn btn-success btn-sm" style="white-space:nowrap">💳 Пополнить</a>',
            url,
        )

    def has_add_permission(self, request):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        try:
            balance = UserBalance.objects.get(pk=object_id)
            extra_context["topup_url"] = reverse(
                "admin:billing_user_topup", args=[balance.pk]
            )
            extra_context["payment_history"] = Payment.objects.filter(
                user=balance.user
            ).order_by("-created_at")[:15]
        except UserBalance.DoesNotExist:
            pass
        return super().change_view(request, object_id, form_url, extra_context)


# ── Payment Admin ─────────────────────────────────────────────────────────────


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "created_at_display",
        "user_link",
        "minutes_badge",
        "amount_display",
        "method_badge",
        "admin_display",
        "note_short",
    ]
    list_filter = ["payment_method", "created_at"]
    search_fields = ["user__username", "admin__username", "note"]
    readonly_fields = [
        "user",
        "admin",
        "amount_paid",
        "minutes_added",
        "payment_method",
        "note",
        "created_at",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Дата", ordering="created_at")
    def created_at_display(self, obj):
        return format_html(
            '<span style="font-size:12px;color:#adb5bd">{}</span>',
            obj.created_at.strftime("%d.%m.%Y %H:%M"),
        )

    @admin.display(description="Пользователь", ordering="user__username")
    def user_link(self, obj):
        if obj.user:
            return format_html(
                '<span style="font-weight:600">{}</span>', obj.user.username
            )
        return "—"

    @admin.display(description="Минуты", ordering="minutes_added")
    def minutes_badge(self, obj):
        h = obj.minutes_added // 60
        m = obj.minutes_added % 60
        label = f"{h}ч {m}м" if h else f"{m}м"
        return format_html(
            '<span style="background:#0d6efd;color:#fff;padding:2px 8px;border-radius:10px;font-weight:600">+{}</span>',
            label,
        )

    @admin.display(description="Сумма", ordering="amount_paid")
    def amount_display(self, obj):
        return format_html(
            '<span style="color:#0dcaf0;font-weight:700">{}</span>',
            f"{obj.amount_paid:,.2f}",
        )

    @admin.display(description="Способ")
    def method_badge(self, obj):
        colors = {"cash": "#198754", "card": "#0d6efd", "transfer": "#6f42c1"}
        labels = {"cash": "💵 Наличные", "card": "💳 Карта", "transfer": "📱 Перевод"}
        color = colors.get(obj.payment_method, "#6c757d")
        label = labels.get(obj.payment_method, obj.payment_method)
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;font-size:12px">{}</span>',
            color,
            label,
        )

    @admin.display(description="Администратор")
    def admin_display(self, obj):
        if obj.admin:
            return format_html(
                '<span style="color:#6c757d">{}</span>', obj.admin.username
            )
        return "—"

    @admin.display(description="Примечание")
    def note_short(self, obj):
        if obj.note:
            return obj.note[:40] + ("…" if len(obj.note) > 40 else "")
        return "—"


# ── TariffPlan Admin ──────────────────────────────────────────────────────────


class TariffPriceInline(admin.TabularInline):
    model = TariffPrice
    extra = 0


@admin.register(TariffPlan)
class TariffPlanAdmin(admin.ModelAdmin):
    list_display = [
        "name", "tariff_type", "club",
        "price_display", "duration_display",
        "is_night", "has_schedule", "is_active",
    ]
    list_filter = ["tariff_type", "is_active", "is_night", "club"]
    search_fields = ["name"]
    list_editable = ["is_active"]
    inlines = [TariffPriceInline]

    fieldsets = (
        ("Основное", {"fields": ("name", "tariff_type", "club", "is_active")}),
        ("Цена и длительность", {"fields": ("price", "minutes", "valid_until_time", "life_days")}),
        ("Расписание", {"fields": ("has_schedule", "schedule_days", "schedule_start", "schedule_end")}),
        ("Флаги", {"fields": ("is_night", "apply_discount")}),
    )

    @admin.display(description="Цена", ordering="price")
    def price_display(self, obj):
        return format_html(
            '<span style="color:#0dcaf0;font-weight:700">{}</span>',
            f"{obj.price:,.0f} с.",
        )

    @admin.display(description="Длительность", ordering="minutes")
    def duration_display(self, obj):
        return format_html(
            '<span style="background:#0d6efd;color:#fff;padding:2px 8px;border-radius:10px;font-weight:600">{}</span>',
            obj.hours_display,
        )


# ── Analytics Admin ───────────────────────────────────────────────────────────


@admin.register(AnalyticsMetrics)
class AnalyticsMetricsAdmin(admin.ModelAdmin):
    change_list_template = "admin/billing/analytics_dashboard.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Calculate Finance Metrics
        total_payments = Payment.objects.aggregate(t=Sum("amount_paid"))["t"] or 0
        payments_today = Payment.objects.filter(created_at__date=timezone.now().date()).aggregate(t=Sum("amount_paid"))["t"] or 0
        total_minutes = Payment.objects.aggregate(t=Sum("minutes_added"))["t"] or 0

        # Calculate Users
        total_users = User.objects.count()
        
        # Determine Top games
        # Based on total players and hours across sessions
        # Assuming you have total_players / total_hours_played properties or we just aggregate
        # For simplicity, let's fetch games and sort them manually or through annotation
        games = list(Game.objects.filter(is_active=True))
        games.sort(key=lambda g: g.total_hours_played, reverse=True)
        top_games = games[:5]

        # Recent income dynamics (last 7 days)
        last_7_days = timezone.now().date() - timezone.timedelta(days=7)
        income_chart_data = list(
            Payment.objects.filter(created_at__date__gte=last_7_days)
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(daily_total=Sum("amount_paid"))
            .order_by("date")
        )

        labels = [item["date"].strftime('%d.%m') for item in income_chart_data]
        values = [float(item["daily_total"]) for item in income_chart_data]

        extra_context.update({
            "title": "Дашборд клуба",
            "total_payments": f"{total_payments:,.0f}",
            "payments_today": f"{payments_today:,.0f}",
            "total_hours": round(total_minutes / 60, 1),
            "total_users": total_users,
            "top_games": top_games,
            "chart_labels": labels,
            "chart_values": values,
        })
        
        return super().changelist_view(request, extra_context=extra_context)


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

from apps.billing.models.shift import Shift

@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("__str__", "start_time", "end_time", "is_active", "initial_cash", "total_revenue", "closing_cash", "discrepancy")
    list_filter = ("is_active", "start_time", "admin")
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.cash_register_view),
                name="billing_cash_register",
            ),
            path(
                "close_shift_action/",
                self.admin_site.admin_view(self.close_shift_action_view),
                name="billing_close_shift_action",
            ),
            path(
                "open_shift_action/",
                self.admin_site.admin_view(self.open_shift_action_view),
                name="billing_open_shift_action",
            )
        ]
        return custom_urls + urls

    def cash_register_view(self, request):
        from django.shortcuts import render
        active_shift = Shift.get_active_shift()
        
        # Determine current stats if shift is active
        if active_shift:
            from apps.billing.models.payment import Payment
            payments = Payment.objects.filter(admin=active_shift.admin, created_at__gte=active_shift.start_time)
            current_cash = sum(p.amount_paid for p in payments if p.payment_method == "cash")
            current_card = sum(p.amount_paid for p in payments if p.payment_method == "card")
            current_total = current_cash + current_card
            
            # X-Report snapshot
            x_report = {
                "initial": active_shift.initial_cash,
                "cash": current_cash,
                "card": current_card,
                "total": current_total,
                "expected": active_shift.initial_cash + current_cash
            }
        else:
            x_report = None
            
        recent_shifts = Shift.objects.order_by('-start_time')[:5]
        
        context = dict(
            self.admin_site.each_context(request),
            title="Касса и Смены (Cash Register)",
            active_shift=active_shift,
            x_report=x_report,
            recent_shifts=recent_shifts
        )
        return render(request, "admin/billing/cash_register.html", context)

    def close_shift_action_view(self, request):
        from django.shortcuts import redirect
        from django.contrib import messages
        from decimal import Decimal
        
        if request.method == "POST":
            closing_cash = request.POST.get('closing_cash', 0)
            try:
                closing_cash = Decimal(closing_cash)
            except:
                closing_cash = Decimal('0.00')
                
            active_shift = Shift.get_active_shift()
            if active_shift:
                active_shift.close_shift(closing_cash)
                messages.success(request, f"Смена успешно закрыта! Z-Отчет сгенерирован. Недостача: {active_shift.discrepancy} руб.")
            else:
                messages.error(request, "Нет активной смены для закрытия.")
                
        return redirect('admin:billing_cash_register')

    def open_shift_action_view(self, request):
        from django.shortcuts import redirect
        from django.contrib import messages
        from decimal import Decimal
        from django.utils import timezone
        
        if request.method == "POST":
            # Check if one is already open
            if Shift.get_active_shift():
                messages.error(request, "Ошибка: Другая смена уже открыта. Сначала закройте её.")
                return redirect('admin:billing_cash_register')
                
            initial_cash = request.POST.get('initial_cash', 0)
            try:
                initial_cash = Decimal(initial_cash)
            except:
                initial_cash = Decimal('0.00')
                
            Shift.objects.create(
                admin=request.user,
                start_time=timezone.now(),
                initial_cash=initial_cash,
                is_active=True
            )
            messages.success(request, f"Смена открыта! Наличные на старте: {initial_cash} руб.")
            
        return redirect('admin:billing_cash_register')
