"""Batch 7 — regressions covering already-applied fixes (money + session correctness)."""
from decimal import Decimal

import pytest


# ── An order can only be paid once (double-pay → second Payment / double debit) ─
@pytest.mark.django_db
def test_order_cannot_be_paid_twice(api, make_club, make_user):
    from apps.computers.models import Computer
    from apps.shops.models import Order
    from apps.billing.models import Payment
    club = make_club()
    client = make_user()
    pc = Computer.objects.create(name="PC-order-double", club=club)
    order = Order.objects.create(account=client, computer=pc,
                                 total_price=Decimal("100"), status="PENDING")

    api.force_authenticate(user=club.owner)
    r1 = api.post(f"/api/v1/shops/orders/admin/{order.id}/pay/", {"payment_method": "cash"}, format="json")
    assert r1.status_code == 200, r1.content
    r2 = api.post(f"/api/v1/shops/orders/admin/{order.id}/pay/", {"payment_method": "cash"}, format="json")
    assert r2.status_code == 400  # already PROCESSING → rejected
    assert Payment.objects.filter(note__contains=f"Заказ #{order.id}").count() == 1


# ── GameSession.end_session is idempotent (no hour double-counting on retry) ──
@pytest.mark.django_db
def test_game_session_end_is_idempotent(make_user, make_club):
    from apps.computers.models import Computer
    from apps.games.models import Game, GameSession, SessionStatus
    user = make_user()
    club = make_club()
    pc = Computer.objects.create(name="PC-gs-idem", club=club)
    game = Game.objects.create(name="GameX", slug="gamex")
    s = GameSession.objects.create(account=user, game=game, computer=pc)

    s.start_session()
    s.refresh_from_db()
    assert s.session_status == SessionStatus.ACTIVE

    s.end_session()
    s.refresh_from_db()
    first_hours = s.total_hours_played
    assert s.session_status == SessionStatus.ENDED

    # A duplicate/retried end call must NOT add hours again.
    s.end_session()
    s.refresh_from_db()
    assert s.total_hours_played == first_hours
    assert s.session_status == SessionStatus.ENDED
