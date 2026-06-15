from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Task(models.Model):
    """Operator task — used by Dashboard «Активные / Завершённые задачи» widget."""

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_tasks",
    )

    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")

    is_finished = models.BooleanField(default=False)
    finished_at = models.DateTimeField(null=True, blank=True)
    finished_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="finished_tasks",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_tasks"
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ["is_finished", "-created_at"]
        indexes = [
            models.Index(fields=["club", "is_finished"]),
            models.Index(fields=["assigned_to", "is_finished"]),
        ]

    def __str__(self):
        return f"{self.title} {'✓' if self.is_finished else '○'}"
