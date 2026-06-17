"""Regression: creating a combo with component products must persist them — the nested
items were read_only and silently dropped, so every combo saved empty."""
import pytest


@pytest.mark.django_db
def test_combo_create_persists_product_items(api, make_club, make_product):
    from apps.shops.models import Combo
    club = make_club()
    product = make_product(club, price="50")

    api.force_authenticate(user=club.owner)
    resp = api.post(
        f"/api/v1/shops/combos/?club={club.id}",
        {"name": "Комбо1", "base_price": "100", "sale_price": "80",
         "product_items": [{"product": product.id, "qty": 2}]},
        format="json",
    )
    assert resp.status_code in (200, 201), resp.content

    combo = Combo.objects.get(name="Комбо1", club=club)
    assert combo.product_items.count() == 1
    item = combo.product_items.first()
    assert item.product_id == product.id
    assert item.qty == 2
