from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.computers.models import Computer, ComputerStatus
from apps.games.models import GameSession, SessionStatus


@shared_task
def check_computer_heartbeats():
    """
    Check all computers for missing heartbeats and mark them as OFFLINE.

    This task runs every 60 seconds via Celery Beat.
    If a computer hasn't sent a heartbeat in the last 60 seconds and is marked ONLINE,
    it will be marked as OFFLINE and any active gaming sessions will be ended.

    Returns:
        dict: Summary of computers marked offline and sessions ended
    """
    threshold_time = timezone.now() - timedelta(seconds=60)

    # Find computers that are ONLINE but haven't sent heartbeat in 60+ seconds
    stale_computers = Computer.objects.filter(
        status=ComputerStatus.ONLINE, last_seen__lt=threshold_time
    )

    computers_marked_offline = 0
    sessions_ended = 0

    for computer in stale_computers:
        # Mark computer as OFFLINE
        computer.status = ComputerStatus.OFFLINE
        computer.save(update_fields=["status"])
        computers_marked_offline += 1

        # End any active sessions on this computer
        active_sessions = GameSession.objects.filter(
            computer=computer, session_status=SessionStatus.ACTIVE
        )

        for session in active_sessions:
            session.end_session()
            sessions_ended += 1

    return {
        "computers_marked_offline": computers_marked_offline,
        "sessions_ended": sessions_ended,
        "threshold_time": threshold_time.isoformat(),
    }


@shared_task
def cleanup_old_metrics():
    """
    Clean up old computer metrics data older than 30 days.

    This task runs daily to prevent database bloat.
    Keeps the last 30 days of metrics data for each computer.

    Returns:
        dict: Number of metrics deleted
    """
    from apps.computers.models import ComputerMetrics

    threshold_date = timezone.now() - timedelta(days=30)

    deleted_count, _ = ComputerMetrics.objects.filter(
        timestamp__lt=threshold_date
    ).delete()

    return {
        "metrics_deleted": deleted_count,
        "threshold_date": threshold_date.isoformat(),
    }
