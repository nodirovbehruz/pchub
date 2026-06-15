"""Periodic booking lifecycle tasks (run by Celery Beat every minute).

Enforces two club settings that were previously stored but never applied:
  • booking_expiry_min     — auto-cancel a no-show booking N min after its start.
  • end_before_booking_min — free a PC N min before a booking starts (end the
                             session on the booked hosts so the booker can sit down).
"""

from celery import shared_task


@shared_task(name="apps.bookings.tasks.process_booking_lifecycle")
def process_booking_lifecycle():
    """Single sweep over ACTIVE bookings, scoped per club by its settings."""
    from django.utils import timezone
    from datetime import timedelta

    from apps.bookings.models import Booking, BookingStatus
    from apps.clubs.models import ClubSettings

    now = timezone.now()
    result = {"expired": 0, "freed_pcs": 0}

    active = (
        Booking.objects.filter(status=BookingStatus.ACTIVE)
        .select_related("club")
        .prefetch_related("hosts")
    )
    for b in active:
        club_id = b.club_id

        # 1) No-show expiry: booking started > N min ago and nobody redeemed it.
        expiry = ClubSettings.get_int(club_id, "booking_expiry_min", 0)
        if expiry and now > b.from_at + timedelta(minutes=expiry):
            b.status = BookingStatus.CANCELED
            b.save(update_fields=["status"])
            result["expired"] += 1
            continue

        # 2) End sessions shortly before the booking begins, so the seat is free.
        before = ClubSettings.get_int(club_id, "end_before_booking_min", 0)
        if before and b.from_at - timedelta(minutes=before) <= now < b.from_at:
            for pc in b.hosts.all():
                if _free_pc_for_booking(pc):
                    result["freed_pcs"] += 1

    return result


def _free_pc_for_booking(pc) -> bool:
    """End any active (guest postpaid) session on a PC and lock it back. Best-effort."""
    try:
        from apps.accounts.models import CustomUser
        from apps.clubs.models import UserClubProfile
        from apps.billing.services.implementation.billing import BillingService
        from apps.computers.models import ComputerCommand
        from apps.computers.models.command import CommandType, CommandStatus
        from apps.computers.models.enums import ComputerStatus

        freed = False
        guest = CustomUser.objects.filter(username=f"guest-pc-{pc.id}").first()
        if guest and UserClubProfile.objects.filter(
            user=guest, club_id=pc.club_id, session_mode="postpaid", is_active=True
        ).exists():
            BillingService().close_guest_postpaid(
                computer=pc, payment_method="cash", admin=None, club_id=pc.club_id
            )
            freed = True

        # Also finish an active REAL ClientSession (not just guest postpaid) and revoke
        # the seated client, else a paying customer is locked under a running timer.
        try:
            from apps.sessions_.models import ClientSession, ClientSessionStatus
            from django.utils import timezone as _tz
            active = ClientSession.objects.filter(
                status=ClientSessionStatus.ACTIVE, hosts__computer=pc,
            ).select_related("client")
            for cs in active:
                cs.status = ClientSessionStatus.FINISHED
                cs.finished_at = _tz.now()
                cs.save(update_fields=["status", "finished_at"])
                cu = cs.client
                if cu:
                    try:
                        cu.is_active_session = False
                        cu.active_hardware_id = ""
                        cu.save(update_fields=["is_active_session", "active_hardware_id"])
                        from realtime.broadcast import push_balance
                        push_balance(cu.pk, {"minutes_remaining": 0, "formatted_time": "00:00",
                                             "has_access": False, "session_mode": "prepaid"})
                    except Exception:
                        pass
                    freed = True
        except Exception:
            pass

        if pc.status != ComputerStatus.OFFLINE:
            pc.status = ComputerStatus.OFFLINE
            pc.save(update_fields=["status"])
            freed = True

        # Lock the shell back to the login screen for the incoming booker.
        ComputerCommand.objects.create(
            computer=pc, command_type=CommandType.LOCK,
            status=CommandStatus.PENDING, payload={"reason": "booking"},
        )
        return freed
    except Exception:
        return False
