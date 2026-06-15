from django.contrib import admin
from django.utils.html import format_html

from apps.computers.models import ComputerGame
from apps.games.models import Game, GameSession, Tag, Category, ClubAccount


class GameInstallationInline(admin.TabularInline):
    """Inline to show which computers have this game installed"""

    model = ComputerGame
    extra = 0
    fields = [
        "computer",
        "is_installed",
        "install_size_gb",
        "install_path",
        "last_played",
    ]
    readonly_fields = ["last_played"]
    verbose_name = "Computer Installation"
    verbose_name_plural = "Installed on Computers"
    fk_name = "game"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("computer")


class GameSessionInline(admin.TabularInline):
    """Inline to show recent game sessions"""

    model = GameSession
    extra = 0
    fields = [
        "account",
        "computer",
        "total_hours_played",
        "session_status",
        "last_played",
    ]
    readonly_fields = ["total_hours_played", "last_played"]
    verbose_name = "Game Session"
    verbose_name_plural = "Recent Sessions"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("account", "computer")
            .order_by("-last_played")
        )


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = [
        "name_display",
        "app_id",
        "platform",
        "developer",
        "tags_display",
        "installations_display",
        "players_display",
        "hours_display",
        "status_display",
    ]
    list_filter = ["is_active", "platform", "is_senet_library", "tags", "created_at", "developer", "publisher"]
    search_fields = ["name", "app_id", "slug", "developer", "publisher"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["tags"]
    readonly_fields = [
        "header_image_preview",
        "icon_preview",
        "text_image_preview",
        "total_players",
        "total_hours_played",
        "installation_count",
        "created_at",
        "updated_at",
    ]
    inlines = [GameInstallationInline, GameSessionInline]
    
    class Media:
        js = ("js/admin_file_picker.js",)

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "slug", "category", "is_senet_library", "description"), "classes": ("wide",)},
        ),
        (
            "Platform & App ID",
            {
                "fields": (
                    "platform",
                    "app_id",
                    ("icon", "icon_preview"),
                    ("header_image", "header_image_preview"),
                    ("text_image", "text_image_preview"),
                ),
                "classes": ("wide",),
            },
        ),
        ("Launch Path Setup", {"fields": ("executable_path", "arguments"), "classes": ("wide",)}),
        ("Categorization", {"fields": ("tags",)}),
        ("Metadata", {"fields": ("developer", "publisher", "release_date")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Statistics",
            {
                "fields": ("installation_count", "total_players", "total_hours_played"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Game")
    def name_display(self, obj):
        if obj.icon:
            return format_html(
                '<div style="display: flex; align-items: center;">'
                '<img src="{}" width="32" height="32" style="border-radius: 4px; margin-right: 10px;"/> '
                '<strong style="font-size: 14px;">{}</strong>'
                "</div>",
                obj.icon.url,
                obj.name,
            )
        return format_html("<strong>{}</strong>", obj.name)

    @admin.display(description="Installations")
    def installations_display(self, obj):
        count = obj.installations.filter(is_installed=True).count()
        color = "#28a745" if count > 5 else "#17a2b8" if count > 0 else "#6c757d"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 14px; font-weight: bold; font-size: 12px;">📦 {}</span>',
            color,
            count,
        )

    @admin.display(description="Players")
    def players_display(self, obj):
        count = obj.total_players
        color = "#28a745" if count > 10 else "#ffc107" if count > 0 else "#6c757d"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 14px; font-weight: bold; font-size: 12px;">👥 {}</span>',
            color,
            count,
        )

    @admin.display(description="Total Hours")
    def hours_display(self, obj):
        hours = float(obj.total_hours_played)
        return format_html(
            '<span style="font-weight: bold; color: #007bff; font-size: 13px;">{}h</span>',
            f"{hours:.1f}",
        )

    @admin.display(description="Tags")
    def tags_display(self, obj):
        tags = obj.tags.all()
        if not tags:
            return format_html(
                '<span style="color: #6c757d; font-style: italic;">No tags</span>'
            )

        tags_html = " ".join(
            [
                f'<span style="background-color: #007bff; color: white; padding: 3px 8px; '
                f'border-radius: 10px; font-size: 11px; margin-right: 4px; display: inline-block;">{tag.name}</span>'
                for tag in tags[:3]  # Show max 3 tags
            ]
        )

        if tags.count() > 3:
            tags_html += f'<span style="color: #6c757d; font-size: 11px;">+{tags.count() - 3}</span>'

        return format_html(tags_html)

    @admin.display(description="Status")
    def status_display(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold; font-size: 12px;">● Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold; font-size: 12px;">● Inactive</span>'
        )

    @admin.display(description="Header Image Preview")
    def header_image_preview(self, obj):
        if obj.header_image:
            return format_html(
                '<img src="{}" style="max-width: 460px; max-height: 215px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"/>',
                obj.header_image.url,
            )
        return "-"

    @admin.display(description="Icon Preview")
    def icon_preview(self, obj):
        if obj.icon:
            return format_html(
                '<img src="{}" style="width: 64px; height: 64px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);"/>',
                obj.icon.url,
            )
        return "-"

    @admin.display(description="Text Image Preview")
    def text_image_preview(self, obj):
        if obj.text_image:
            return format_html(
                '<img src="{}" style="max-width: 320px; max-height: 120px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);"/>',
                obj.text_image.url,
            )
        return "-"

    @admin.display(description="Total Installations")
    def installation_count(self, obj):
        return obj.installations.filter(is_installed=True).count()

    actions = ["activate_games", "deactivate_games", "broadcast_update"]

    @admin.action(description="📢 Broadcast update to ALL PCs")
    def broadcast_update(self, request, queryset):
        from apps.computers.models import Computer, ComputerCommand
        from apps.computers.models.command import CommandType, CommandStatus
        
        active_computers = Computer.objects.filter(is_active=True)
        pc_count = active_computers.count()
        
        commands_created = 0
        for game in queryset:
            for pc in active_computers:
                ComputerCommand.objects.create(
                    computer=pc,
                    game=game,
                    command_type=CommandType.UPDATE,
                    status=CommandStatus.PENDING,
                    payload={
                        "installer_url": game.executable_path,
                        "game_name": game.name
                    },
                    created_by=request.user
                )
                commands_created += 1
                
        self.message_user(
            request, 
            f"Successfully broadcasted update for {queryset.count()} game(s) to {pc_count} computers ({commands_created} commands created)."
        )

    @admin.action(description="✅ Activate selected games")
    def activate_games(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} game(s) activated successfully.")

    @admin.action(description="❌ Deactivate selected games")
    def deactivate_games(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} game(s) deactivated successfully.")


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = [
        "session_info_display",
        "hours_display",
        "session_status_display",
        "last_played",
    ]
    list_filter = ["session_status", "last_played", "created_at", "game", "computer"]
    search_fields = ["account__username", "game__name", "computer__name"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "last_played",
        "session_duration_display",
    ]
    date_hierarchy = "last_played"
    list_per_page = 50

    fieldsets = (
        (
            "Session Information",
            {"fields": ("account", "game", "computer"), "classes": ("wide",)},
        ),
        (
            "Play Time",
            {
                "fields": (
                    "total_hours_played",
                    "current_session_start",
                    "session_duration_display",
                    "session_status",
                ),
                "classes": ("wide",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("last_played", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Session Info")
    def session_info_display(self, obj):
        game_icon = (
            f'<img src="{obj.game.icon.url}" width="24" height="24" style="border-radius: 4px; vertical-align: middle; margin-right: 8px;"/>'
            if obj.game.icon
            else ""
        )
        return format_html(
            '<div style="line-height: 1.6;">'
            "{}"
            '<strong style="font-size: 13px;">{}</strong><br>'
            '<small style="color: #007bff;">👤 {}</small> • '
            '<small style="color: #6c757d;">💻 {}</small>'
            "</div>",
            game_icon,
            obj.game.name,
            obj.account.username,
            obj.computer.name,
        )

    @admin.display(description="Hours Played")
    def hours_display(self, obj):
        hours = float(obj.total_hours_played)
        if hours > 100:
            color = "#dc3545"
            icon = "🔥"
        elif hours > 50:
            color = "#ffc107"
            icon = "⭐"
        elif hours > 10:
            color = "#28a745"
            icon = "✓"
        else:
            color = "#17a2b8"
            icon = "▸"

        return format_html(
            '<span style="font-weight: bold; color: {}; font-size: 14px;">{} {}h</span>',
            color,
            icon,
            f"{hours:.1f}",
        )

    @admin.display(description="Status")
    def session_status_display(self, obj):
        status_config = {
            "ACTIVE": {"color": "#28a745", "icon": "▶️", "text": "Playing"},
            "PAUSED": {"color": "#ffc107", "icon": "⏸️", "text": "Paused"},
            "ENDED": {"color": "#6c757d", "icon": "⏹️", "text": "Ended"},
        }
        config = status_config.get(obj.session_status, status_config["ENDED"])
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 12px; '
            'border-radius: 14px; font-size: 11px; font-weight: bold;">{} {}</span>',
            config["color"],
            config["icon"],
            config["text"],
        )

    @admin.display(description="Current Session Duration")
    def session_duration_display(self, obj):
        if obj.current_session_start and obj.session_status == "ACTIVE":
            from django.utils import timezone

            duration = timezone.now() - obj.current_session_start
            hours = duration.total_seconds() / 3600
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{:.1f} hours (ongoing)</span>',
                hours,
            )
        return "-"

    actions = ["end_active_sessions"]

    @admin.action(description="⏹️ End active sessions")
    def end_active_sessions(self, request, queryset):
        active_sessions = queryset.filter(session_status="ACTIVE")
        for session in active_sessions:
            session.end_session()
        count = active_sessions.count()
        self.message_user(request, f"{count} session(s) ended successfully.")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "game_count_display", "created_at"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Tag Information",
            {"fields": ("name", "slug", "description"), "classes": ("wide",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description="Games")
    def game_count_display(self, obj):
        count = obj.games.count()
        color = "#28a745" if count > 10 else "#17a2b8" if count > 0 else "#6c757d"
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; '
            'border-radius: 14px; font-weight: bold; font-size: 12px;">🎮 {}</span>',
            color,
            count,
        )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "order"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["order", "name"]
    list_editable = ["order"]


@admin.register(ClubAccount)
class ClubAccountAdmin(admin.ModelAdmin):
    list_display = ["login", "platform", "is_active", "is_in_use", "games_count"]
    list_filter = ["platform", "is_active", "is_in_use"]
    search_fields = ["login"]
    filter_horizontal = ["games"]

    @admin.display(description="Games associated")
    def games_count(self, obj):
        return obj.games.count()
