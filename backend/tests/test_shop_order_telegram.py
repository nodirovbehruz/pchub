"""Ordering from the shell shop must surface to staff: (1) club Telegram, AND (2) the
in-app operator bell — an AdminCall is created so the 🔔 badge lights up and the order
shows in «Вызовы». Both best-effort from CreateOrderAPIView, club from the order's PC."""
import pytest


def _setup_order(make_club, make_product, make_user):
    from apps.computers.models import Computer
    from apps.shops.models import Cart, CartItem, Stock
    club = make_club()
    buyer = make_user(username="guest-buyer")
    product = make_product(club=club, price="20000", name="Кола")
    Stock.objects.create(product=product, quantity=10)
    Computer.objects.create(club=club, hardware_id="HW-ORD-1", name="PC-5", is_active=True)
    cart = Cart.objects.create(account=buyer)
    CartItem.objects.create(cart=cart, product=product, quantity=2)
    return club, buyer


@pytest.mark.django_db
def test_shop_order_notifies_telegram(api, make_club, make_product, make_user, monkeypatch):
    club, buyer = _setup_order(make_club, make_product, make_user)
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


@pytest.mark.django_db
def test_shop_order_creates_admin_call_for_bell(api, make_club, make_product, make_user):
    from apps.sessions_.models import AdminCall
    club, buyer = _setup_order(make_club, make_product, make_user)
    api.force_authenticate(user=buyer)
    r = api.post("/api/v1/shops/orders/create/", {"hardware_id": "HW-ORD-1"}, format="json")
    assert r.status_code == 201, r.content
    call = AdminCall.objects.filter(club=club, answered_at__isnull=True).first()
    assert call is not None, "no AdminCall created → order won't show in the bell"
    assert "Заказ" in call.note and "Кола" in call.note
    assert call.client_id == buyer.id
