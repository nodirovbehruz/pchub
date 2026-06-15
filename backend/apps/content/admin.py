from django.contrib import admin

from .models import News, Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "assigned_to", "is_finished", "created_at")
    list_filter = ("club", "is_finished")
    search_fields = ("title", "body")
    list_editable = ("is_finished",)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "club", "is_published", "show_from", "show_until", "created_at")
    list_filter = ("club", "is_published")
    search_fields = ("title", "body")
    list_editable = ("is_published",)
