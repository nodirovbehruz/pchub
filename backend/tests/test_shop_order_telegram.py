"""Ordering from the shell shop must send a Telegram notification to the club so staff
know what a client ordered and on which PC. notify_club is invoked best-effort from
CreateOrderAPIView with club resolved from the order's computer."""
import pytest


@pytest.mark.django_db
def test_shop_order_notifies_club(api, make_club, make_product, make_user, monkeypatch):
    from apps.computers.models import Computer
    from apps.shops.models import Cart, CartItem, Stock

    club = make_club()
    buyer = make_user(username="guest-buyer")
    product = make_product(club=club, price="20000", name="Кола")
    Stock.objects.create(product=product, quantity=10)
    Computer.objects.create(club=club, hardware_id="HW-ORD-1", name="PC-5", is_active=True)
    cart = Cart.objects.create(account=buyer)
    CartItem.objects.create(cart=cart, product=product, quantity=2)

    sent = {}
    monkeypatch.setattr(
        "apps.clubs.services.telegram.notify_club",
        lambda club_id, message: sent.update(club_id=club_id, message=message),
    )

    api.force_authenticate(user=buyer)
    r = api.post("/api/v1/shops/orders/create/", {"hardware_id": "HW-ORD-1"}, format="json")
    assert r.status_code == 201, r.content
    assert sent.get("club_id") == club.id
    msg = sent.get("message", "")
    assert "Новый заказ" in msg and "Кола" in msg and "PC-5" in msg
