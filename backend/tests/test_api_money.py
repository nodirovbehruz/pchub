"""Money-flow regression tests for audit fixes."""
from decimal import Decimal

import pytest


# ── POS balance sale with insufficient deposit must roll back stock ──────────
# Bug: a `return Response(...)` inside transaction.atomic() COMMITTED the already-
# applied stock decrement (and combo minutes) on a rejected sale → free goods.
@pytest.mark.django_db
def test_pos_insufficient_funds_rolls_back_stock(api, make_club, make_user, make_profile, make_product):
    from apps.shops.models import Stock
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("0"))  # no money
    product = make_product(club, price="100.00")
    Stock.objects.create(product=product, quantity=5)

    api.force_authenticate(user=club.owner)
    resp = api.post(
        f"/api/v1/shops/sell/?club={club.id}",
        {"items": [{"kind": "products", "id": product.id, "qty": 1}],
         "payment_method": "balance", "client_id": client.id},
        format="json",
    )
    assert resp.status_code >= 400  # sale rejected
    Stock.objects.get(product=product).refresh_from_db()
    assert Stock.objects.get(product=product).quantity == 5  # stock NOT consumed


@pytest.mark.django_db
def test_pos_sale_with_enough_deposit_succeeds_and_decrements(api, make_club, make_user, make_profile, make_product):
    from apps.shops.models import Stock
    club = make_club()
    client = make_user()
    make_profile(client, club, deposit_money=Decimal("500"))
    product = make_product(club, price="100.00")
    Stock.objects.create(product=product, quantity=5)

    api.force_authenticate(user=club.owner)
    resp = api.post(
        f"/api/v1/shops/sell/?club={club.id}",
        {"items": [{"kind": "products", "id": product.id, "qty": 2}],
         "payment_method": "balance", "client_id": client.id},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.content
    assert Stock.objects.get(product=product).quantity == 3  # 5 - 2


# ── personal_discount must be clamped to 0..100 (negative price = free money) ─
@pytest.mark.django_db
def test_personal_discount_rejects_out_of_range(api, make_club, make_user, make_profile):
    club = make_club()
    client = make_user()
    prof = make_profile(client, club, personal_discount=0)

    api.force_authenticate(user=club.owner)
    resp = api.patch(
        f"/api/v1/billing/admin/users/{client.id}/profile/?club={club.id}",
        {"personal_discount": 150}, format="json",
    )
    # The fix clamps to 0..100 (rather than 400); the security invariant is that a value
    # >100 is NEVER stored — that's what made ClientBuyTariff compute a negative price.
    assert resp.status_code in (200, 400)
    prof.refresh_from_db()
    assert 0 <= prof.personal_discount <= 100
