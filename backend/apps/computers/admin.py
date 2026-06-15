import json

from django import forms
from django.contrib import admin
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.shortcuts import render

from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from django.views.decorators.http import require_POST

from apps.computers.models import Computer, ComputerGame, ComputerMetrics, AppRelease, MapElement, GuestSession, ComputerGroup
from apps.computers.models.command import CommandStatus, CommandType, ComputerCommand

from apps.games.models import Game, GameSession
from apps.billing.models.balance import UserBalance
from apps.billing.models.shift import Shift


User = get_user_model()


@admin.register(ComputerGroup)
class ComputerGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "club", "computers_count", "color_swatch", "position", "is_active")
    list_filter = ("club", "is_active")
    search_fields = ("name", "club__name")
    list_editable = ("position", "is_active")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("club_id", "position", "name")

    @admin.display(description="Color")
    def color_swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:18px;height:18px;border-radius:4px;'
            'background:{};border:1px solid rgba(255,255,255,.2)"></span> <code>{}</code>',
            obj.color, obj.color,
        )


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display = ["version", "file_link", "created_at", "is_active"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["version", "description"]
    readonly_fields = ["created_at", "file_url_display"]

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">📄 Download {}</a>', obj.file.url, obj.version)
        return "-"
    file_link.short_description = "File URL"

    def file_url_display(self, obj):
        if obj.file:
            return format_html(
                '<code style="background: #f8f9fa; padding: 10px; display: block; border: 1px solid #ddd;">{}</code>'
                '<p class="help">Copy this URL and paste it into the "Installer URL" field when creating an Update Application command.</p>',
                obj.file.url
            )
        return "No file uploaded yet."
    file_url_display.short_description = "Copy this URL for Update Command"



@admin.register(MapElement)
class MapElementAdmin(admin.ModelAdmin):
    list_display = ["element_type", "position_x", "position_y", "width", "height", "rotation"]
    list_filter = ["element_type"]


# ── Custom form for ComputerCommand ──────────────────────────────────────────
# Exposes the JSON payload as individual human-readable fields instead of raw JSON.


class ComputerCommandForm(forms.ModelForm):
    installer_url = forms.CharField(
        required=False,
        label="Installer URL / network path",
        help_text="http(s):// URL or UNC path (\\\\server\\share\\setup.exe) or local path",
        widget=forms.TextInput(attrs={"style": "width:100%"}),
    )
    install_args = forms.CharField(
        required=False,
        initial="/S",
        label="Installer arguments",
        help_text="Silent-install flags, e.g. /S  /silent  /quiet  /D=C:\\Games\\MyGame",
        widget=forms.TextInput(attrs={"style": "width:100%"}),
    )
    install_path = forms.CharField(
        required=False,
        label="Install destination path (optional)",
        help_text="Leave empty to use the installer's default location",
        widget=forms.TextInput(attrs={"style": "width:100%"}),
    )
    uninstall_path = forms.CharField(
        required=False,
        label="Uninstaller path",
        help_text="Full path to uninstall.exe — required for uninstall / reinstall commands",
        widget=forms.TextInput(attrs={"style": "width:100%"}),
    )

    class Meta:
        model = ComputerCommand
        fields = ["computer", "game", "command_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.payload:
            p = self.instance.payload
            self.fields["installer_url"].initial = p.get("installer_url", "")
            self.fields["install_args"].initial = p.get("install_args", "/S")
            self.fields["install_path"].initial = p.get("install_path", "")
            self.fields["uninstall_path"].initial = p.get("uninstall_path", "")

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.payload = {
            "installer_url": self.cleaned_data.get("installer_url", ""),
            "install_args": self.cleaned_data.get("install_args", "/S"),
            "install_path": self.cleaned_data.get("install_path", ""),
            "uninstall_path": self.cleaned_data.get("uninstall_path", ""),
        }
        if commit:
            instance.save()
        return instance


class ComputerCommandInline(admin.TabularInline):
    """Create/view software commands directly from the Computer record."""

    model = ComputerCommand
    form = ComputerCommandForm
    extra = 1
    max_num = 5
    fields = [
        "command_type",
        "game",
        "installer_url",
        "install_args",
        "install_path",
        "uninstall_path",
        "status",
        "error_message",
    ]
    readonly_fields = ["status", "error_message"]
    verbose_name = "Software Command"
    verbose_name_plural = "📦 Software Commands (remote install / uninstall / update)"
    show_change_link = True

    def get_queryset(self, request):
        return (
            super().get_queryset(request).select_related("game").order_by("-created_at")
        )

    def save_new_objects(self, formset, commit=True):
        objects = super().save_new_objects(formset, commit=False)
        for obj in objects:
            if not obj.pk:
                obj.created_by = (
                    formset.request.user if hasattr(formset, "request") else None
                )
            if commit:
                obj.save()
        return objects


# ─────────────────────────────────────────────────────────────────────────────


class InstalledGamesInline(admin.TabularInline):
    """Inline to show installed games on this computer"""

    model = ComputerGame
    extra = 0
    fields = ["game", "is_installed", "install_size_gb", "install_path", "last_played"]
    readonly_fields = ["last_played"]
    verbose_name = "Installed Game"
    verbose_name_plural = "Installed Games"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("game")
            .order_by("-is_installed", "-last_played")
        )


class ComputerSessionsInline(admin.TabularInline):
    """Inline to show gaming sessions on this computer"""

    model = GameSession
    extra = 0
    max_num = 10  # Limit to 10 sessions
    fields = ["account", "game", "total_hours_played", "session_status", "last_played"]
    readonly_fields = ["total_hours_played", "last_played"]
    verbose_name = "Gaming Session"
    verbose_name_plural = "Recent Gaming Sessions"
    fk_name = "computer"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("account", "game")
            .order_by("-last_played")
        )


@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = [
        "computer_info_display",
        "active_user_display",
        "status_display",
        "specs_display",
        "games_display",
        "last_seen",
    ]
    list_filter = ["status", "is_active", "last_seen", "os_name"]
    search_fields = ["pc_number", "name", "slug", "owner__username", "ip_address", "hardware_id"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = [
        "hardware_id",
        "specs_summary_display",
        "installed_games_count",
        "total_gaming_hours",
        "latest_metrics_display",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "last_seen"
    inlines = [InstalledGamesInline, ComputerSessionsInline, ComputerCommandInline]

    # ── Club Map URLs ────────────────────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "club-map/",
                self.admin_site.admin_view(self.club_map_view),
                name="computers_club_map",
            ),
            path(
                "club-map/save/",
                self.admin_site.admin_view(self.save_map_positions),
                name="computers_save_map",
            ),
            path(
                "club-map/create-element/",
                self.admin_site.admin_view(self.create_map_element),
                name="computers_create_element",
            ),
            path(
                "club-map/delete-element/",
                self.admin_site.admin_view(self.delete_map_element),
                name="computers_delete_element",
            ),
            path(
                "club-map/status-api/",
                self.admin_site.admin_view(self.map_status_api),
                name="computers_map_status",
            ),
            path(
                "club-map/bulk-command/",
                self.admin_site.admin_view(self.bulk_command_api),
                name="computers_bulk_command",
            ),
            path(
                "club-map/admin-action/",
                self.admin_site.admin_view(self.admin_action_api),
                name="computers_admin_action",
            ),
            path(
                "club-map/shift-status/",
                self.admin_site.admin_view(self.get_shift_info_api),
                name="computers_shift_status",
            ),
            path(
                "club-map/open-shift/",
                self.admin_site.admin_view(self.open_shift_api),
                name="computers_open_shift",
            ),
            path(
                "club-map/close-shift/",
                self.admin_site.admin_view(self.close_shift_api),
                name="computers_close_shift",
            ),
            path(
                "club-map/abonements-api/",
                self.admin_site.admin_view(self.abonements_api),
                name="computers_abonements_api",
            ),
            path(
                "club-map/purchase-abonement/",
                self.admin_site.admin_view(self.purchase_abonement_api),
                name="computers_purchase_abonement",
            ),

        ]
        return custom + urls

    def purchase_abonement_api(self, request):
        import json
        from apps.billing.models import Abonement, PurchasedAbonement, UserBalance
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "POST required"})
        
        try:
            data = json.loads(request.body)
            pc_id = data.get("pc_id")
            ab_id = data.get("ab_id")
            
            pc = Computer.objects.get(id=pc_id)
            abonement = Abonement.objects.get(id=ab_id)
            
            # Find active user on this PC or handle guest
            active_user = User.objects.filter(
                active_hardware_id=pc.hardware_id,
                is_active_session=True
            ).first()

            if not active_user:
                return JsonResponse({"success": False, "error": "На ПК нет активного пользователя. Сначала залогиньте игрока."})

            # 1. Create Purchase record
            PurchasedAbonement.objects.create(
                user=active_user,
                abonement=abonement,
                is_used=True
            )
            
            # 2. Add time to user balance
            balance, _ = UserBalance.objects.get_or_create(user=active_user)
            balance.add_minutes(abonement.duration_minutes)
            
            # 3. Send UNLOCK/UPDATE command to PC
            ComputerCommand.objects.create(
                computer=pc,
                command_type=CommandType.UNLOCK,
                created_by=request.user
            )
            
            return JsonResponse({
                "success": True, 
                "message": f"Абонемент '{abonement.name}' продан. Добавлено {abonement.duration_minutes} мин."
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def club_map_view(self, request):
        computers = Computer.objects.select_related("owner").all()
        elements = MapElement.objects.all()
        shift = Shift.get_active_shift()
        
        # Active guest sessions

        active_guests = {gs.computer_id: gs for gs in GuestSession.objects.filter(is_active=True)}
        
        status_map = {
            "ONLINE": "online",
            "OFFLINE": "offline",
            "MAINTENANCE": "offline",
            "DISABLED": "offline",
        }
        for c in computers:
            c.status = status_map.get(c.status, "offline")
            if c.id in active_guests:
                c.status = "guest"
                c.guest_session = active_guests[c.id]
            elif c.hardware_id:
                active_user = User.objects.filter(
                    active_hardware_id=c.hardware_id,
                    is_active_session=True
                ).first()
                if active_user:
                    c.status = "busy"
                    c.owner = active_user

        context = {
            **self.admin_site.each_context(request),
            "title": "Карта клуба",
            "computers": computers,
            "elements": elements,
            "active_shift": shift,
        }
        return render(request, "admin/computers/club_map.html", context)


    def admin_action_api(self, request):
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "POST required"})
            
        import json
        from apps.billing.models import Shift, Payment, PaymentMethod
        from apps.billing.services import topup_user
        from decimal import Decimal

        try:
            data = json.loads(request.body)
            action = data.get("action")
            pc_id = data.get("pc_id")
            pc = Computer.objects.get(id=pc_id)

            if action == 'LOGIN_USER':
                username = data.get("username")
                user = User.objects.get(username=username)
                
                # Link user to PC for active session tracking
                user.active_hardware_id = pc.hardware_id
                user.is_active_session = True
                user.save(update_fields=["active_hardware_id", "is_active_session"])
                
                ComputerCommand.objects.create(
                    computer=pc,
                    command_type=CommandType.LOGIN,
                    payload={"username": username},
                    created_by=request.user
                )

            elif action == 'LOGIN_GUEST':
                if not Shift.get_active_shift():
                    return JsonResponse({"success": False, "error": "Откройте смену для генерации чека!"})
                amount_str = data.get("amount", "0")
                amount = Decimal(amount_str)
                method_str = data.get("method", "cash").upper()
                method = PaymentMethod.CASH if method_str == "CASH" else PaymentMethod.CARD
                
                # Check how many minutes it buys (rough estimate, 3000 UZS = 60 mins -> 50 UZS/min)
                # We'll just create a guest session
                GuestSession.objects.create(
                    computer=pc,
                    rate_per_hour=3000,
                    is_active=True
                )
                
                # Create Payment into shift
                Payment.objects.create(
                    amount_paid=amount,
                    payment_method=method,
                    initiator=request.user,
                    is_successful=True,
                    note=f"Чек на сумму {amount} руб."
                )

                ComputerCommand.objects.create(
                    computer=pc,
                    command_type=CommandType.UNLOCK,
                    created_by=request.user
                )

            elif action == 'LOGIN_POSTPAY':
                # Similar to guest session, but post-pay
                GuestSession.objects.create(
                    computer=pc,
                    rate_per_hour=3000,
                    is_active=True,
                    total_amount=Decimal('0') # Postpay starts at 0
                )
                ComputerCommand.objects.create(
                    computer=pc,
                    command_type=CommandType.UNLOCK,
                    created_by=request.user
                )

            elif action == 'TOPUP':
                if not Shift.get_active_shift():
                    return JsonResponse({"success": False, "error": "Откройте смену!"})
                
                amount_str = data.get("amount", "0")
                amount = Decimal(amount_str)
                method_str = data.get("method", "cash").upper()
                method = PaymentMethod.CASH if method_str == "CASH" else PaymentMethod.CARD

                active_user = User.objects.filter(
                    active_hardware_id=pc.hardware_id,
                    is_active_session=True
                ).first()

                if active_user:
                    # Minutes = amount / 50 (based on 3000/60)
                    minutes = int(amount / Decimal('50'))
                    topup_user(
                        user_id=str(active_user.id),
                        minutes=minutes,
                        amount_paid=amount,
                        payment_method=method,
                        admin=request.user,
                        note="Пополнение баланса по нормеру ПК"
                    )
                else:
                    gs = GuestSession.objects.filter(computer=pc, is_active=True).first()
                    if gs:
                        # Log extra payment for check
                        Payment.objects.create(
                            amount_paid=amount,
                            payment_method=method,
                            initiator=request.user,
                            is_successful=True,
                            note=f"Доп. пополнение по чеку"
                        )
                    else:
                        return JsonResponse({"success": False, "error": "Нет активного пользователя или чека на этом ПК"})

            elif action == 'END_SESSION':
                # Clear User
                active_user = User.objects.filter(
                    active_hardware_id=pc.hardware_id,
                    is_active_session=True
                ).first()
                if active_user:
                    active_user.active_hardware_id = ""
                    active_user.is_active_session = False
                    active_user.save(update_fields=["active_hardware_id", "is_active_session"])
                
                # Clear Guest
                gs = GuestSession.objects.filter(computer=pc, is_active=True).first()
                if gs:
                    gs.end_time = timezone.now()
                    gs.is_active = False
                    if not gs.total_amount:
                        gs.total_amount = gs.calculate_cost()
                    gs.save()

                # Lock PC
                ComputerCommand.objects.create(
                    computer=pc,
                    command_type=CommandType.LOCK,
                    created_by=request.user
                )

            return JsonResponse({"success": True})
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "Пользователь не найден"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def bulk_command_api(self, request):
        if request.method != "POST": return JsonResponse({"success":False})
        import json
        try:
            data = json.loads(request.body)
            ids = data.get("ids", [])
            cmd_type = data.get("command")
            
            computers = Computer.objects.filter(id__in=ids)
            for pc in computers:
                ComputerCommand.objects.create(
                    computer=pc,
                    command_type=cmd_type,
                    created_by=request.user
                )
            return JsonResponse({"success": True, "count": computers.count()})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def abonements_api(self, request):
        from apps.billing.models import Abonement
        abs_qs = Abonement.objects.filter(is_active=True)
        data = [
            {
                "id": a.id,
                "name": a.name,
                "price": float(a.price),
                "duration": a.duration_minutes,
            }
            for a in abs_qs
        ]
        return JsonResponse({"abonements": data})

    def save_map_positions(self, request):
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "POST required"})
        try:
            data = json.loads(request.body)
            # Update Computers
            positions = data.get("positions", [])
            for pos in positions:
                Computer.objects.filter(id=pos["id"]).update(
                    position_x=pos["x"],
                    position_y=pos["y"]
                )
            # Update Elements
            elements = data.get("elements", [])
            for el in elements:
                MapElement.objects.filter(id=el["id"]).update(
                    position_x=el["x"],
                    position_y=el["y"],
                    width=el.get("w", 100),
                    height=el.get("h", 40),
                    rotation=el.get("r", 0)
                )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def create_map_element(self, request):
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "POST required"})
        try:
            data = json.loads(request.body)
            element = MapElement.objects.create(
                element_type=data.get("type"),
                position_x=data.get("x", 100),
                position_y=data.get("y", 100),
            )
            return JsonResponse({"success": True, "id": element.id})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def delete_map_element(self, request):
        if request.method != "POST":
            return JsonResponse({"success": False, "error": "POST required"})
        try:
            data = json.loads(request.body)
            MapElement.objects.filter(id=data.get("id")).delete()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    def map_status_api(self, request):
        computers = Computer.objects.select_related("owner").all()
        shift = Shift.get_active_shift()
        active_guests = {gs.computer_id: gs for gs in GuestSession.objects.filter(is_active=True)}
        result = []

        # ...

        status_map = {
            "ONLINE": "online",
            "OFFLINE": "offline",
            "MAINTENANCE": "offline",
            "DISABLED": "offline",
        }
        for c in computers:
            css_status = status_map.get(c.status, "offline")
            user = None
            balance = 0
            tariff = "Standard"
            
            if c.id in active_guests:
                css_status = "guest"
                gs = active_guests[c.id]
                user = f"Guest #{gs.id}"
                balance = gs.duration_minutes
                tariff = "Pay-after-play"
            elif c.hardware_id:
                active_user = User.objects.filter(
                    active_hardware_id=c.hardware_id,
                    is_active_session=True
                ).select_related("balance").first()
                if active_user:
                    css_status = "busy"
                    user = active_user.username
                    balance = active_user.balance.minutes_remaining if hasattr(active_user, "balance") else 0
            
            result.append({
                "id": c.id,
                "status": css_status,
                "user": user,
                "balance": balance,
                "tariff": tariff,
                "hardware": c.hardware_id or "N/A"
            })

        return JsonResponse({
            "computers": result,
            "shift": {
                "is_active": shift is not None,
                "admin": shift.admin.username if shift else None,
                "start": shift.start_time.strftime("%H:%M") if shift else None
            }
        })

    def get_shift_info_api(self, request):
        shift = Shift.get_active_shift()
        return JsonResponse({
            "is_active": shift is not None,
            "admin": shift.admin.username if shift else None,
            "start_time": shift.start_time.isoformat() if shift else None,
            "revenue": float(shift.total_revenue) if shift else 0
        })

    def open_shift_api(self, request):
        if Shift.get_active_shift():
            return JsonResponse({"success": False, "error": "Shift already open"})
        Shift.objects.create(admin=request.user)
        return JsonResponse({"success": True})

    def close_shift_api(self, request):
        shift = Shift.get_active_shift()
        if not shift:
            return JsonResponse({"success": False, "error": "No active shift"})
        shift.close_shift()
        return JsonResponse({"success": True})

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("pc_number", "name", "slug", "description", "owner", "hardware_id"),
                "classes": ("wide",),
            },
        ),
        (
            "Hardware Specifications",
            {
                "fields": (
                    ("cpu_model", "cpu_cores", "cpu_threads"),
                    ("ram_total_gb", "gpu_model"),
                    "storage_total_gb",
                    "specs_summary_display",
                ),
                "classes": ("wide",),
            },
        ),
        ("Operating System", {"fields": ("os_name", "os_version")}),
        ("Network", {"fields": ("ip_address", "mac_address")}),
        (
            "Status & Activity",
            {"fields": ("status", "is_active", "last_seen"), "classes": ("wide",)},
        ),
        (
            "Map Position",
            {
                "fields": (("position_x", "position_y"), "map_zone"),
                "classes": ("wide",),
                "description": "Position of this PC on the interactive club map. Use the map editor to drag & drop.",
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "installed_games_count",
                    "total_gaming_hours",
                    "latest_metrics_display",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        from django.urls import reverse
        extra_context["club_map_url"] = reverse("admin:computers_club_map")
        extra_context["show_map_button"] = True
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Computer")
    def computer_info_display(self, obj):
        status_icon = {
            "ONLINE": "🟢",
            "OFFLINE": "⚫",
            "MAINTENANCE": "🟡",
            "DISABLED": "🔴",
        }.get(obj.status, "⚫")

        return format_html(
            '<div style="line-height: 1.5;">'
            '<strong style="font-size: 14px;">{} <span style="color: #6f42c1;">PC #{}</span> • {}</strong><br>'
            '<small style="color: #6c757d;">💻 {} • {}</small>'
            "</div>",
            status_icon,
            obj.pc_number or "?",
            obj.name,
            obj.os_name or "Unknown OS",
            obj.ip_address or "No IP",
        )

    @admin.display(description="Пользователь")
    def active_user_display(self, obj):
        if not obj.hardware_id:
            return format_html('<span style="color: #6c757d;">-</span>')
            
        # Optimization: in a real club, finding the active user for the PC
        user = User.objects.filter(
            active_hardware_id=obj.hardware_id, 
            is_active_session=True
        ).first()

        if user:
            return format_html(
                '<div style="line-height: 1.2;">'
                '<strong style="color: #28a745; font-size: 13px;">👤 {}</strong><br>'
                '<small style="color: #17a2b8; font-weight: 600;">В игре</small>'
                '</div>',
                user.username,
            )
        return format_html('<span style="color: #6c757d;">Свободен</span>')

    @admin.display(description="Владелец")
    def owner_display(self, obj):
        if obj.owner:
            return format_html(
                '<span style="color: #007bff; font-weight: 500;">👤 {}</span>',
                obj.owner.username,
            )
        return format_html('<span style="color: #6c757d;">-</span>')

    @admin.display(description="Status")
    def status_display(self, obj):
        status_config = {
            "ONLINE": {"color": "#28a745", "icon": "●", "bg": "#d4edda"},
            "OFFLINE": {"color": "#6c757d", "icon": "●", "bg": "#e2e3e5"},
            "MAINTENANCE": {"color": "#ffc107", "icon": "●", "bg": "#fff3cd"},
            "DISABLED": {"color": "#dc3545", "icon": "●", "bg": "#f8d7da"},
        }
        config = status_config.get(obj.status, status_config["OFFLINE"])
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 5px 12px; '
            'border-radius: 14px; font-weight: bold; font-size: 11px;">{} {}</span>',
            config["bg"],
            config["color"],
            config["icon"],
            obj.get_status_display(),
        )

    @admin.display(description="Specs")
    def specs_display(self, obj):
        specs = []
        if obj.cpu_model:
            cores = f" ({obj.cpu_cores}C/{obj.cpu_threads}T)" if obj.cpu_cores else ""
            specs.append(f"🔧 {obj.cpu_model[:30]}{cores}")
        if obj.ram_total_gb:
            specs.append(f"🎮 {obj.ram_total_gb}GB RAM")
        if obj.gpu_model:
            specs.append(f"🎨 {obj.gpu_model[:30]}")
        return format_html(
            '<div style="font-size: 11px; line-height: 1.4;">{}</div>',
            "<br>".join(specs) if specs else "-",
        )

    @admin.display(description="Installed Games")
    def games_display(self, obj):
        count = obj.installed_games_count
        if count > 10:
            color = "#28a745"
            icon = "🎮"
        elif count > 5:
            color = "#17a2b8"
            icon = "🎮"
        elif count > 0:
            color = "#ffc107"
            icon = "🎮"
        else:
            color = "#6c757d"
            icon = "📦"

        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 14px; '
            'border-radius: 14px; font-weight: bold; font-size: 12px;">{} {}</span>',
            color,
            icon,
            count,
        )

    @admin.display(description="Gaming Hours")
    def gaming_hours_display(self, obj):
        hours = float(obj.total_gaming_hours)
        if hours > 100:
            color = "#dc3545"
        elif hours > 50:
            color = "#ffc107"
        elif hours > 0:
            color = "#28a745"
        else:
            color = "#6c757d"

        return format_html(
            '<span style="font-weight: bold; color: {}; font-size: 13px;">{:.1f}h</span>',
            color,
            hours,
        )

    @admin.display(description="Hardware Specs Summary")
    def specs_summary_display(self, obj):
        return format_html(
            '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff;">'
            '<div style="margin-bottom: 8px;"><strong>💻 CPU:</strong> {} ({} cores / {} threads)</div>'
            '<div style="margin-bottom: 8px;"><strong>🎮 RAM:</strong> {} GB</div>'
            '<div style="margin-bottom: 8px;"><strong>🎨 GPU:</strong> {}</div>'
            "<div><strong>💾 Storage:</strong> {} GB</div>"
            "</div>",
            obj.cpu_model or "N/A",
            obj.cpu_cores or "N/A",
            obj.cpu_threads or "N/A",
            obj.ram_total_gb or "N/A",
            obj.gpu_model or "N/A",
            obj.storage_total_gb or "N/A",
        )

    @admin.display(description="Latest Metrics")
    def latest_metrics_display(self, obj):
        metrics = obj.latest_metrics
        if metrics:
            cpu_val = f"{metrics.cpu_usage_percent:.1f}%" if metrics.cpu_usage_percent is not None else "N/A"
            ram_usage = f"{metrics.ram_usage_percent:.1f}%" if metrics.ram_usage_percent is not None else "N/A"
            ram_used = f"{metrics.ram_used_gb:.1f}" if metrics.ram_used_gb is not None else "N/A"
            
            try:
                ram_total_val = metrics.ram_used_gb + metrics.ram_available_gb
                ram_total = f"{ram_total_val:.1f}"
            except:
                ram_total = "N/A"

            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">'
                "<div><strong>CPU:</strong> {} ({})</div>"
                "<div><strong>RAM:</strong> {} ({}/{} GB)</div>"
                "<div><strong>Updated:</strong> {}</div>"
                "</div>",
                cpu_val,
                metrics.cpu_status,
                ram_usage,
                ram_used,
                ram_total,
                metrics.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            )
        return format_html('<span style="color: #6c757d;">No metrics available</span>')

    actions = [
        "mark_online",
        "mark_offline",
        "mark_maintenance",
        "mark_disabled",
        "send_install_command",
        "send_uninstall_command",
        "send_reinstall_command",
        "send_update_command",
    ]

    @admin.action(description="🟢 Mark as Online")
    def mark_online(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(status="ONLINE", last_seen=timezone.now())
        self.message_user(request, f"{updated} computer(s) marked as online.")

    @admin.action(description="⚫ Mark as Offline")
    def mark_offline(self, request, queryset):
        updated = queryset.update(status="OFFLINE")
        self.message_user(request, f"{updated} computer(s) marked as offline.")

    @admin.action(description="🟡 Mark as Maintenance")
    def mark_maintenance(self, request, queryset):
        updated = queryset.update(status="MAINTENANCE")
        self.message_user(request, f"{updated} computer(s) marked for maintenance.")

    @admin.action(description="🔴 Mark as Disabled")
    def mark_disabled(self, request, queryset):
        updated = queryset.update(status="DISABLED")
        self.message_user(request, f"{updated} computer(s) disabled.")

    # ── Software management actions ───────────────────────────────────────────
    # These create pending commands that the PC client will pick up and execute.

    def _bulk_command(self, request, queryset, command_type, description):
        created = 0
        for computer in queryset:
            ComputerCommand.objects.create(
                computer=computer,
                command_type=command_type,
                created_by=request.user,
                payload={
                    "installer_url": "",
                    "install_args": "/S",
                    "install_path": "",
                    "uninstall_path": "",
                },
            )
            created += 1
        self.message_user(
            request,
            f"📦 {description} command created for {created} computer(s) with empty payload. "
            "Go to Software Commands → edit each command to add the installer/uninstaller path, "
            "then the PC client will execute it within 30 seconds.",
        )

    @admin.action(description="📥 Queue INSTALL command on selected computers")
    def send_install_command(self, request, queryset):
        self._bulk_command(request, queryset, CommandType.INSTALL, "Install")

    @admin.action(description="🗑️ Queue UNINSTALL command on selected computers")
    def send_uninstall_command(self, request, queryset):
        self._bulk_command(request, queryset, CommandType.UNINSTALL, "Uninstall")

    @admin.action(description="♻️ Queue REINSTALL command on selected computers")
    def send_reinstall_command(self, request, queryset):
        self._bulk_command(request, queryset, CommandType.REINSTALL, "Reinstall")

    @admin.action(description="⬆️ Queue UPDATE command on selected computers")
    def send_update_command(self, request, queryset):
        self._bulk_command(request, queryset, CommandType.UPDATE, "Update")


@admin.register(ComputerGame)
class ComputerGameAdmin(admin.ModelAdmin):
    list_display = [
        "installation_display",
        "installed_status_display",
        "size_display",
        "last_played",
    ]
    list_filter = ["is_installed", "installed_at", "last_played", "computer", "game"]
    search_fields = ["game__name", "computer__name", "install_path"]
    readonly_fields = ["installed_at", "updated_at"]
    date_hierarchy = "installed_at"
    list_per_page = 50

    fieldsets = (
        (
            "Installation Details",
            {"fields": ("computer", "game", "is_installed"), "classes": ("wide",)},
        ),
        (
            "Installation Info",
            {
                "fields": ("install_path", "install_size_gb", "last_played"),
                "classes": ("wide",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("installed_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Installation")
    def installation_display(self, obj):
        # Build img tag via format_html so it is marked safe and won't be
        # double-escaped when passed as an argument to the outer format_html.
        if obj.game.icon:
            game_icon = format_html(
                '<img src="{}" width="32" height="32"'
                ' style="border-radius:4px;margin-right:10px;vertical-align:middle;"/>',
                obj.game.icon.url,
            )
        else:
            game_icon = format_html("")

        computer_status_icon = {
            "ONLINE": "🟢",
            "OFFLINE": "⚫",
            "MAINTENANCE": "🟡",
            "DISABLED": "🔴",
        }.get(obj.computer.status, "⚫")

        game_type_label = (
            f"Steam ID: {obj.game.steam_app_id}"
            if obj.game.steam_app_id
            else "Local game"
        )
        return format_html(
            '<div style="display:flex;align-items:center;line-height:1.6;">'
            "{}"
            "<div>"
            '<strong style="font-size:13px;">{}</strong><br>'
            '<small style="color:#6c757d;">{} {} • {}</small>'
            "</div>"
            "</div>",
            game_icon,
            obj.game.name,
            computer_status_icon,
            obj.computer.name,
            game_type_label,
        )

    @admin.display(description="Status")
    def installed_status_display(self, obj):
        if obj.is_installed:
            return format_html(
                '<span style="background-color: #d4edda; color: #28a745; padding: 5px 12px; '
                'border-radius: 14px; font-weight: bold; font-size: 11px;">✓ Installed</span>'
            )
        return format_html(
            '<span style="background-color: #f8d7da; color: #dc3545; padding: 5px 12px; '
            'border-radius: 14px; font-weight: bold; font-size: 11px;">✗ Uninstalled</span>'
        )

    @admin.display(description="Size")
    def size_display(self, obj):
        if obj.install_size_gb:
            size = float(obj.install_size_gb)
            if size > 100:
                color = "#dc3545"
                icon = "💾"
            elif size > 50:
                color = "#ffc107"
                icon = "💿"
            else:
                color = "#28a745"
                icon = "📀"
            return format_html(
                '<span style="font-weight: bold; color: {}; font-size: 13px;">{} {:.1f} GB</span>',
                color,
                icon,
                size,
            )
        return format_html('<span style="color: #6c757d;">-</span>')

    actions = ["mark_installed", "mark_uninstalled"]

    @admin.action(description="✅ Mark as Installed")
    def mark_installed(self, request, queryset):
        updated = queryset.update(is_installed=True)
        self.message_user(request, f"{updated} game(s) marked as installed.")

    @admin.action(description="❌ Mark as Uninstalled")
    def mark_uninstalled(self, request, queryset):
        updated = queryset.update(is_installed=False)
        self.message_user(request, f"{updated} game(s) marked as uninstalled.")


@admin.register(ComputerMetrics)
class ComputerMetricsAdmin(admin.ModelAdmin):
    list_display = [
        "computer_info_display",
        "cpu_display",
        "ram_display",
        "disk_display",
        "network_display",
        "timestamp",
    ]
    list_filter = ["timestamp", "computer"]
    search_fields = ["computer__name"]
    readonly_fields = ["cpu_status", "ram_status", "timestamp", "metrics_visualization"]
    date_hierarchy = "timestamp"
    list_per_page = 100

    fieldsets = (
        ("Computer", {"fields": ("computer",), "classes": ("wide",)}),
        (
            "Metrics Overview",
            {"fields": ("metrics_visualization",), "classes": ("wide",)},
        ),
        (
            "CPU Metrics",
            {
                "fields": ("cpu_usage_percent", "cpu_temperature", "cpu_status"),
                "classes": ("wide",),
            },
        ),
        (
            "RAM Metrics",
            {
                "fields": (
                    "ram_used_gb",
                    "ram_available_gb",
                    "ram_usage_percent",
                    "ram_status",
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Disk Metrics",
            {"fields": ("disk_used_gb", "disk_available_gb"), "classes": ("collapse",)},
        ),
        (
            "Network Metrics",
            {
                "fields": ("network_upload_mbps", "network_download_mbps"),
                "classes": ("collapse",),
            },
        ),
        ("Timestamp", {"fields": ("timestamp",)}),
    )

    @admin.display(description="Computer")
    def computer_info_display(self, obj):
        if not obj.pk or not obj.computer:
            return "-"
            
        status_icon = {
            "ONLINE": "🟢",
            "OFFLINE": "⚫",
            "MAINTENANCE": "🟡",
            "DISABLED": "🔴",
        }.get(obj.computer.status, "⚫")

        return format_html(
            '<div style="line-height: 1.5;">'
            '<strong style="font-size: 13px;">{} {}</strong><br>'
            '<small style="color: #6c757d;">💻 {}</small>'
            "</div>",
            status_icon,
            obj.computer.name,
            obj.computer.ip_address or "No IP",
        )

    @admin.display(description="CPU")
    def cpu_display(self, obj):
        status_colors = {
            "critical": "#dc3545",
            "high": "#ffc107",
            "medium": "#17a2b8",
            "low": "#28a745",
        }
        color = status_colors.get(obj.cpu_status, "#6c757d")
        temp_display = f" • {obj.cpu_temperature}°C" if obj.cpu_temperature else ""
        usage_val = f"{obj.cpu_usage_percent:.1f}%" if obj.cpu_usage_percent is not None else "N/A"

        return format_html(
            '<div style="line-height: 1.5;">'
            '<span style="color: {}; font-weight: bold; font-size: 14px;">{}</span><br>'
            '<small style="color: #6c757d;">{}{}</small>'
            "</div>",
            color,
            usage_val,
            obj.cpu_status.upper(),
            temp_display,
        )

    @admin.display(description="RAM")
    def ram_display(self, obj):
        if obj.ram_used_gb is None or obj.ram_available_gb is None or obj.ram_usage_percent is None:
            return "-"
            
        status_colors = {
            "critical": "#dc3545",
            "high": "#ffc107",
            "medium": "#17a2b8",
            "low": "#28a745",
        }
        color = status_colors.get(obj.ram_status, "#6c757d")
        usage_val = f"{obj.ram_usage_percent:.1f}%" if obj.ram_usage_percent is not None else "N/A"
        used_val = f"{obj.ram_used_gb:.1f}" if obj.ram_used_gb is not None else "N/A"
        
        try:
            total_val = obj.ram_used_gb + obj.ram_available_gb
            total_str = f"{total_val:.1f}"
        except:
            total_str = "N/A"

        return format_html(
            '<div style="line-height: 1.5;">'
            '<span style="color: {}; font-weight: bold; font-size: 14px;">{}</span><br>'
            '<small style="color: #6c757d;">{}/{} GB • {}</small>'
            "</div>",
            color,
            usage_val,
            used_val,
            total_str,
            obj.ram_status.upper(),
        )

    @admin.display(description="Disk")
    def disk_display(self, obj):
        if obj.disk_used_gb and obj.disk_available_gb:
            total_disk = obj.disk_used_gb + obj.disk_available_gb
            usage_percent = (
                (obj.disk_used_gb / total_disk) * 100 if total_disk > 0 else 0
            )

            if usage_percent > 90:
                color = "#dc3545"
            elif usage_percent > 75:
                color = "#ffc107"
            else:
                color = "#28a745"

            return format_html(
                '<div style="line-height: 1.5;">'
                '<span style="color: {}; font-weight: bold; font-size: 14px;">{:.1f}%</span><br>'
                '<small style="color: #6c757d;">{:.0f}/{:.0f} GB</small>'
                "</div>",
                color,
                usage_percent,
                obj.disk_used_gb,
                total_disk,
            )
        return format_html('<span style="color: #6c757d;">-</span>')

    @admin.display(description="Network")
    def network_display(self, obj):
        if obj.network_upload_mbps or obj.network_download_mbps:
            return format_html(
                '<div style="line-height: 1.5;">'
                "<small>Up: {:.1f} Mbps</small><br>"
                "<small>Down: {:.1f} Mbps</small>"
                "</div>",
                obj.network_upload_mbps or 0,
                obj.network_download_mbps or 0,
            )
        return format_html('<span style="color: #6c757d;">-</span>')

    @admin.display(description="Metrics Visualization")
    def metrics_visualization(self, obj):
        if not obj.pk or obj.cpu_usage_percent is None or obj.ram_usage_percent is None:
            return format_html('<div style="color: #6c757d; padding: 10px;">Visualization will be available after saving.</div>')

        def get_bar(percentage, label):
            if percentage > 90:
                color = "#dc3545"
            elif percentage > 75:
                color = "#ffc107"
            elif percentage > 50:
                color = "#17a2b8"
            else:
                color = "#28a745"

            return f"""
                <div style="margin-bottom: 15px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                        <strong>{label}</strong>
                        <span style="color: {color}; font-weight: bold;">{percentage:.1f}%</span>
                    </div>
                    <div style="background: #e9ecef; border-radius: 10px; height: 20px; overflow: hidden;">
                        <div style="background: {color}; width: {percentage}%; height: 100%; border-radius: 10px; transition: width 0.3s;"></div>
                    </div>
                </div>
            """

        total_ram = (obj.ram_used_gb or 0) + (obj.ram_available_gb or 0)
        total_disk = (
            (obj.disk_used_gb or 0) + (obj.disk_available_gb or 0)
            if obj.disk_used_gb is not None and obj.disk_available_gb is not None
            else 0
        )
        disk_usage = (obj.disk_used_gb / total_disk * 100) if total_disk > 0 else 0

        html = '<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">'
        html += get_bar(obj.cpu_usage_percent, f"CPU Usage ({obj.cpu_status})")
        html += get_bar(
            obj.ram_usage_percent,
            f"RAM Usage ({obj.ram_status}) - {(obj.ram_used_gb or 0):.1f}/{total_ram:.1f} GB",
        )

        if total_disk > 0:
            html += get_bar(
                disk_usage, f"Disk Usage - {obj.disk_used_gb:.0f}/{total_disk:.0f} GB"
            )

        if obj.network_download_mbps or obj.network_upload_mbps:
            html += f"""
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                    <strong>Network:</strong>
                    <div style="display: flex; gap: 20px; margin-top: 8px;">
                        <div>Upload: <strong>{obj.network_upload_mbps or 0:.1f} Mbps</strong></div>
                        <div>Download: <strong>{obj.network_download_mbps or 0:.1f} Mbps</strong></div>
                    </div>
                </div>
            """

        html += "</div>"
        return format_html(html)


@admin.register(ComputerCommand)
class ComputerCommandAdmin(admin.ModelAdmin):
    form = ComputerCommandForm
    list_display = [
        "id",
        "computer",
        "game_display",
        "command_type_display",
        "status_display",
        "payload_summary",
        "created_by",
        "created_at",
    ]
    list_filter = ["command_type", "status", "created_at"]
    search_fields = ["computer__name", "game__name", "created_by__username"]
    readonly_fields = [
        "status",
        "error_message",
        "created_at",
        "updated_at",
        "created_by",
    ]
    date_hierarchy = "created_at"
    list_per_page = 50

    fieldsets = (
        (
            "Target",
            {"fields": ("computer", "game"), "classes": ("wide",)},
        ),
        (
            "Command",
            {
                "fields": ("command_type",),
                "classes": ("wide",),
                "description": (
                    "<strong>install</strong> — run the installer on the remote PC.<br>"
                    "<strong>reinstall</strong> — uninstall first, then run the installer.<br>"
                    "<strong>uninstall</strong> — run the uninstaller silently.<br>"
                    "<strong>update</strong> — run the new installer over the existing installation."
                ),
            },
        ),
        (
            "Installer / Uninstaller details",
            {
                "fields": (
                    "installer_url",
                    "install_args",
                    "install_path",
                    "uninstall_path",
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Result (read-only)",
            {
                "fields": (
                    "status",
                    "error_message",
                    "created_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["cancel_selected", "requeue_failed"]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # ── List display helpers ──────────────────────────────────────────────────

    @admin.display(description="Game / Software")
    def game_display(self, obj):
        return (
            obj.game.name
            if obj.game
            else format_html('<span style="color:#6c757d">—</span>')
        )

    @admin.display(description="Command")
    def command_type_display(self, obj):
        icons = {
            CommandType.INSTALL: ("📥", "#0d6efd"),
            CommandType.REINSTALL: ("♻️", "#6610f2"),
            CommandType.UNINSTALL: ("🗑️", "#dc3545"),
            CommandType.UPDATE: ("⬆️", "#198754"),
        }
        icon, color = icons.get(obj.command_type, ("?", "#6c757d"))
        return format_html(
            '<span style="color:{};font-weight:bold">{} {}</span>',
            color,
            icon,
            obj.get_command_type_display(),
        )

    @admin.display(description="Status")
    def status_display(self, obj):
        colors = {
            CommandStatus.PENDING: ("#fff3cd", "#856404"),
            CommandStatus.IN_PROGRESS: ("#cce5ff", "#004085"),
            CommandStatus.COMPLETED: ("#d4edda", "#155724"),
            CommandStatus.FAILED: ("#f8d7da", "#721c24"),
            CommandStatus.CANCELLED: ("#e2e3e5", "#383d41"),
        }
        bg, fg = colors.get(obj.status, ("#e2e3e5", "#383d41"))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:10px;'
            'font-size:11px;font-weight:bold">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description="Payload summary")
    def payload_summary(self, obj):
        p = obj.payload or {}
        url = p.get("installer_url", "")
        args = p.get("install_args", "")
        if url:
            short = url[-50:] if len(url) > 50 else url
            return format_html('<code style="font-size:11px">{} {}</code>', short, args)
        return format_html('<span style="color:#6c757d">—</span>')

    # ── Actions ───────────────────────────────────────────────────────────────

    @admin.action(description="❌ Cancel selected commands")
    def cancel_selected(self, request, queryset):
        updated = queryset.filter(status=CommandStatus.PENDING).update(
            status=CommandStatus.CANCELLED
        )
        self.message_user(request, f"{updated} command(s) cancelled.")

    @admin.action(description="🔄 Re-queue failed commands (set back to pending)")
    def requeue_failed(self, request, queryset):
        updated = queryset.filter(status=CommandStatus.FAILED).update(
            status=CommandStatus.PENDING, error_message=""
        )
        self.message_user(request, f"{updated} failed command(s) re-queued as pending.")

    # ── Custom admin page: Software Management ────────────────────────────────

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "software-management/",
                self.admin_site.admin_view(self.software_management_view),
                name="computers_sw_manage",
            ),
            path(
                "software-management/create/",
                self.admin_site.admin_view(self.sw_create_view),
                name="computers_sw_create",
            ),
            path(
                "software-management/list/",
                self.admin_site.admin_view(self.sw_list_view),
                name="computers_sw_list",
            ),
            path(
                "software-management/cancel/<int:command_id>/",
                self.admin_site.admin_view(self.sw_cancel_view),
                name="computers_sw_cancel",
            ),
            path(
                "software-management/requeue/<int:command_id>/",
                self.admin_site.admin_view(self.sw_requeue_view),
                name="computers_sw_requeue",
            ),
        ]
        return custom + urls

    def software_management_view(self, request):
        computers = Computer.objects.order_by("name")
        games = Game.objects.filter(is_active=True).order_by("name")
        context = {
            **self.admin_site.each_context(request),
            "computers": computers,
            "games": games,
            "title": "Software Management",
        }
        return render(request, "admin/computers/software_management.html", context)

    def sw_list_view(self, request):
        qs = ComputerCommand.objects.select_related(
            "computer", "game", "created_by"
        ).order_by("-created_at")[:200]
        commands = [
            {
                "id": c.id,
                "computer_name": c.computer.name,
                "pc_number": c.computer.pc_number,
                "game_name": c.game.name if c.game else None,
                "command_type": c.command_type,
                "status": c.status,
                "payload": c.payload,
                "error_message": c.error_message,
                "created_at": c.created_at.isoformat(),
                "created_by": c.created_by.username if c.created_by else None,
            }
            for c in qs
        ]
        return JsonResponse({"commands": commands})

    def sw_create_view(self, request):
        if request.method != "POST":
            return JsonResponse({"detail": "Method not allowed."}, status=405)
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"detail": "Invalid JSON."}, status=400)

        computer_id = data.get("computer_id")
        game_id = data.get("game_id") or None
        command_type = data.get("command_type")
        payload = data.get("payload", {})

        if not computer_id or not command_type:
            return JsonResponse(
                {"detail": "computer_id and command_type are required."}, status=400
            )
        if command_type not in [ct.value for ct in CommandType]:
            return JsonResponse(
                {"detail": f"Invalid command_type '{command_type}'."}, status=400
            )

        try:
            computer = Computer.objects.get(pk=computer_id)
        except Computer.DoesNotExist:
            return JsonResponse({"detail": "Computer not found."}, status=404)

        game = None
        if game_id:
            try:
                game = Game.objects.get(pk=game_id)
            except Game.DoesNotExist:
                return JsonResponse({"detail": "Game not found."}, status=404)

        command = ComputerCommand.objects.create(
            computer=computer,
            game=game,
            command_type=command_type,
            payload=payload,
            created_by=request.user,
        )
        return JsonResponse({"id": command.id, "status": command.status}, status=201)

    def sw_cancel_view(self, request, command_id):
        if request.method != "POST":
            return JsonResponse({"detail": "Method not allowed."}, status=405)
        try:
            command = ComputerCommand.objects.get(pk=command_id)
        except ComputerCommand.DoesNotExist:
            return JsonResponse({"detail": "Command not found."}, status=404)
        if command.status != CommandStatus.PENDING:
            return JsonResponse(
                {"detail": f"Cannot cancel a '{command.status}' command."}, status=400
            )
        command.status = CommandStatus.CANCELLED
        command.save(update_fields=["status", "updated_at"])
        return JsonResponse({"detail": "Cancelled."})

    def sw_requeue_view(self, request, command_id):
        if request.method != "POST":
            return JsonResponse({"detail": "Method not allowed."}, status=405)
        try:
            command = ComputerCommand.objects.get(pk=command_id)
        except ComputerCommand.DoesNotExist:
            return JsonResponse({"detail": "Command not found."}, status=404)
        if command.status != CommandStatus.FAILED:
            return JsonResponse(
                {
                    "detail": f"Only failed commands can be re-queued (current: '{command.status}')."
                },
                status=400,
            )
        command.status = CommandStatus.PENDING
        command.error_message = ""
        command.save(update_fields=["status", "error_message", "updated_at"])
        return JsonResponse({"detail": "Re-queued."})

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse

        extra_context = extra_context or {}
        extra_context["software_management_url"] = reverse("admin:computers_sw_manage")
        return super().changelist_view(request, extra_context=extra_context)
