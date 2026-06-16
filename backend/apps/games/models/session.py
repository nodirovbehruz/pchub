from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .enums import SessionStatus


class GameSession(models.Model):
    """
    Game session model - tracks hours played per account per game per computer
    Updated by C# application
    """

    # Relationships
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="game_sessions",
        help_text=_("Player account"),
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="sessions",
        help_text=_("Game being played"),
    )
    computer = models.ForeignKey(
        "computers.Computer",
        on_delete=models.CASCADE,
        related_name="game_sessions",
        help_text=_("Computer where game is played"),
    )

    # Session Data
    total_hours_played = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("Total hours played (cumulative)"),
    )

    # Current Session Tracking
    current_session_start = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When current session started (null if not playing)"),
    )
    session_status = models.CharField(
        max_length=10,
        choices=SessionStatus.choices,
        default=SessionStatus.ENDED,
        help_text=_("Current session status"),
    )

    # Last Activity
    last_played = models.DateTimeField(
        auto_now=True, help_text=_("Last time this game was played")
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "game_sessions"
        verbose_name = _("Game Session")
        verbose_name_plural = _("Game Sessions")
        ordering = ["-last_played"]
        unique_together = [["account", "game", "computer"]]
        indexes = [
            models.Index(fields=["account", "game"]),
            models.Index(fields=["computer", "game"]),
            models.Index(fields=["session_status"]),
            models.Index(fields=["-last_played"]),
        ]

    def __str__(self):
        return f"{self.account.username} - {self.game.name} on {self.computer.name}"

    def update_hours(self, hours_to_add: float):
        """
        Add hours to total hours played
        Called by C# app
        """
        from decimal import Decimal
        from django.db.models import F
        from django.utils import timezone
        # F() increment — a final update_hours ping racing end_session used to lose
        # one of the two adds (read-modify-write clobber).
        type(self).objects.filter(pk=self.pk).update(
            total_hours_played=F("total_hours_played") + Decimal(str(hours_to_add)),
            last_played=timezone.now(),
        )
        self.refresh_from_db(fields=["total_hours_played", "last_played"])

    def start_session(self):
        """Start a new gaming session"""
        from django.utils import timezone

        now = timezone.now()
        # Don't reset an already-running session's start — re-starting used to overwrite
        # current_session_start and silently discard the already-elapsed time.
        if self.session_status == SessionStatus.ACTIVE and self.current_session_start:
            return
        # One seat = one active session: close any OTHER still-ACTIVE session on this
        # computer (crediting its elapsed time) before opening a new one. Previously
        # nothing checked occupancy, so a PC could carry several ACTIVE sessions at once.
        for other in (type(self).objects
                      .filter(computer_id=self.computer_id, session_status=SessionStatus.ACTIVE)
                      .exclude(pk=self.pk)):
            other.end_session()
        self.current_session_start = now
        self.session_status = SessionStatus.ACTIVE
        self.save(update_fields=["current_session_start", "session_status"])

    def end_session(self, hours_played: float = None):
        """End current gaming session.

        Idempotent and server-authoritative: only an ACTIVE session can be ended, and
        the duration is computed from current_session_start — NOT from the client's
        hours_played (which let a duplicate/retried end call double-count, or any client
        inflate its own stats). A second end call updates 0 rows and is a no-op.
        """
        from decimal import Decimal
        from django.db.models import F
        from django.utils import timezone

        now = timezone.now()
        active = (type(self).objects
                  .filter(pk=self.pk, session_status=SessionStatus.ACTIVE).first())
        if not active:
            return  # already ended / never started — no-op (idempotent)
        add = Decimal("0")
        if active.current_session_start:
            secs = max(0.0, (now - active.current_session_start).total_seconds())
            add = Decimal(str(secs / 3600.0))
        type(self).objects.filter(pk=self.pk, session_status=SessionStatus.ACTIVE).update(
            current_session_start=None,
            session_status=SessionStatus.ENDED,
            last_played=now,
            total_hours_played=F("total_hours_played") + add,
        )
        self.refresh_from_db()
