from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ClientComment(models.Model):
    """An operator note attached to a client within a club.

    SmartShell: profile → Комментарии tab. Multiple notes per client,
    each can be marked important (highlighted in sale dialog).
    """

    club = models.ForeignKey(
        "clubs.Club",
        on_delete=models.CASCADE,
        related_name="client_comments",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="written_client_comments",
    )
    text = models.TextField(_("Comment"))
    is_important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "client_comments"
        verbose_name = _("Client Comment")
        verbose_name_plural = _("Client Comments")
        ordering = ["-is_important", "-created_at"]

    def __str__(self):
        return f"{self.client} — {self.text[:30]}"
