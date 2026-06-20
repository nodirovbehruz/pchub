"""Regression: refunding a guest «Магазин» (POS, user=NULL) payment must not 500.

The locked re-fetch was Payment.objects.select_for_update().select_related("user"). The
user FK is nullable (guests), so select_related LEFT-JOINs it, and Postgres refuses
FOR UPDATE on the nullable side of an outer join → HTTP 500 on prod. sqlite ignores
FOR UPDATE so this asserts the happy path (200) the fix preserves."""
from decimal import Decimal
import pytest


@pytest.mark.django_db
def test_refund_guest_pos_sale(api, make_club):
    from apps.billing.models import Payment, OperationLog, LogAction
    club = make_club()
    p = Payment.objects.create(user=None, club=club, amount_paid=Decimal("15"),
                               minutes_added=0, payment_method="cash", note="[POS] x1")
    OperationLog.objects.create(club=club, object_type="Payment", object_id=str(p.id),
                                action=LogAction.PAYMENT_CREATE, payload={"items": []})
    api.force_authenticate(user=club.owner)
    r = api.post(f"/api/v1/billing/admin/payments/{p.id}/refund/?club={club.id}",
                 {"club": club.id}, format="json")
    assert r.status_code == 200, r.content
    p.refresh_from_db()
    assert "[REFUNDED]" in p.note
