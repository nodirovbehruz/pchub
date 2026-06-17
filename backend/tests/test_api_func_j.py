"""Regression: a no-show booking must release the PC it had locked (UNLOCK), not leave
it stuck on the lock screen forever."""
from datetime import timedelta

import pytest
from django.utils import timezone


@pytest.mark.django_db
def test_noshow_releases_locked_pc(make_club):
    from apps.computers.models import Computer, ComputerCommand
    from apps.computers.models.command import CommandType, CommandStatus
    from apps.clubs.models import ClubSettings
    from apps.bookings.models import Booking, BookingStatus
    from apps.bookings.tasks import process_booking_lifecycle

    club = make_club()
    ClubSettings.objects.create(club=club, data={"booking_expiry_min": 10})
    pc = Computer.objects.create(name="PC-noshow", club=club)

    now = timezone.now()
    b = Booking.objects.create(club=club, from_at=now - timedelta(minutes=20),
                               to_at=now + timedelta(minutes=40), status=BookingStatus.ACTIVE)
    b.hosts.add(pc)
    # PC was locked to reserve it for the booker.
    lock = ComputerCommand.objects.create(
        computer=pc, command_type=CommandType.LOCK, status=CommandStatus.PENDING,
        payload={"reason": "booking"})

    process_booking_lifecycle()

    b.refresh_from_db()
    lock.refresh_from_db()
    assert b.status == BookingStatus.CANCELED            # no-show cancelled
    assert lock.status == CommandStatus.CANCELLED        # reserve-lock superseded
    assert ComputerCommand.objects.filter(               # shell told to unlock
        computer=pc, command_type=CommandType.UNLOCK, status=CommandStatus.PENDING).exists()
