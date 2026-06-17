"""Batch 5 regressions: global-catalog perms, negative cash order, booking PATCH overlap."""
from datetime import timedelta

import pytest
from django.utils import timezone


# ── Only the platform admin may mutate the GLOBAL game catalog ───────────────
@pytest.mark.django_db
def test_club_owner_cannot_write_global_game_catalog(make_user, make_club):
    from apps.games.api.v1.views.game import IsPlatformAdminOrReadOnly
    perm = IsPlatformAdminOrReadOnly()

    class Req:
        pass

    owner = make_club().owner            # user_type='user'
    admin = make_user(user_type="admin")

    req = Req(); req.method = "PATCH"; req.user = owner
    assert perm.has_permission(req, None) is False   # club owner: no catalog write
    req.user = admin
    assert perm.has_permission(req, None) is True    # platform admin: allowed
    req.method = "GET"; req.user = owner
    assert perm.has_permission(req, None) is True     # read still open


# ── Negative cash order amount must be rejected ──────────────────────────────
@pytest.mark.django_db
def test_cash_order_negative_amount_rejected():
    from apps.billing.api.v1.views.extra import CashOrderSerializer
    s = CashOrderSerializer(data={"type": "rko", "amount": "-50000", "comment": "x"})
    assert not s.is_valid()
    assert "amount" in s.errors
    ok = CashOrderSerializer(data={"type": "rko", "amount": "100.00", "comment": "x"})
    ok.is_valid()
    assert "amount" not in ok.errors


# ── PATCH a booking onto an occupied slot must be rejected (overlap on update) ─
@pytest.mark.django_db
def test_booking_update_overlap_rejected(api, make_club):
    from apps.computers.models import Computer
    from apps.bookings.models import Booking, BookingStatus
    club = make_club()
    pc = Computer.objects.create(name="PC-overlap-1", club=club)
    base = timezone.now().replace(microsecond=0)

    a = Booking.objects.create(club=club, from_at=base + timedelta(hours=2),
                               to_at=base + timedelta(hours=3), status=BookingStatus.ACTIVE)
    a.hosts.add(pc)
    b = Booking.objects.create(club=club, from_at=base + timedelta(hours=4),
                               to_at=base + timedelta(hours=5), status=BookingStatus.ACTIVE)
    b.hosts.add(pc)

    api.force_authenticate(user=club.owner)
    # Move B to overlap A (14:30-15:30 over 14:00-15:00).
    resp = api.patch(
        f"/api/v1/bookings/{b.id}/?club={club.id}",
        {"from_at": (base + timedelta(hours=2, minutes=30)).isoformat(),
         "to_at": (base + timedelta(hours=3, minutes=30)).isoformat()},
        format="json",
    )
    assert resp.status_code == 400, resp.content
    b.refresh_from_db()
    assert b.from_at == base + timedelta(hours=4)  # unchanged
