"""Deep review: shift Z-report revenue accounting."""
from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_shift_total_revenue_includes_genuine_transfer_excludes_deposit(make_club):
    from django.utils import timezone
    from datetime import timedelta
    from apps.billing.models import Shift, Payment
    club = make_club()
    shift = Shift.objects.create(
        admin=club.owner, club=club, initial_cash=Decimal("0"),
        start_time=timezone.now() - timedelta(minutes=1), is_active=True)

    mk = lambda amt, method, note: Payment.objects.create(
        amount_paid=Decimal(amt), payment_method=method, note=note, club_id=club.id,
        minutes_added=0)
    mk("100", "cash", "")                       # cash sale
    mk("50", "card", "")                        # card sale
    mk("200", "transfer", "")                   # GENUINE bank transfer → revenue
    mk("30", "transfer", "[DEPOSIT][POS]")      # deposit-spend → NOT new revenue

    shift.close_shift(closing_cash=Decimal("100"))  # drawer = initial(0)+cash(100)

    assert shift.total_revenue_cash == Decimal("100")          # drawer = cash only
    assert shift.total_revenue == Decimal("350")               # 100+50+200, NOT +30
    assert shift.discrepancy == Decimal("0")                   # closing 100 == expected 100
