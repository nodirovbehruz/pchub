from django.conf import settings
from django.db import models


class ChatMessage(models.Model):
    """A private operator↔PC chat message.

    Each message belongs to one computer's thread. `from_admin` distinguishes an
    operator message from a client/guest message. `is_read` marks whether the
    OTHER side has seen it (used for the operator's unread badge).
    """

    computer = models.ForeignKey(
        "computers.Computer", on_delete=models.CASCADE, related_name="chat_messages"
    )
    club = models.ForeignKey(
        "clubs.Club", on_delete=models.CASCADE, related_name="chat_messages",
        null=True, blank=True,
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="chat_messages",
    )
    from_admin = models.BooleanField(default=False)
    sender_name = models.CharField(max_length=120, blank=True, default="")
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "computer_chat_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["computer", "created_at"]),
            models.Index(fields=["computer", "from_admin", "is_read"]),
        ]

    def __str__(self):
        who = "admin" if self.from_admin else "client"
        return f"[{who}] PC#{self.computer_id}: {self.text[:30]}"
