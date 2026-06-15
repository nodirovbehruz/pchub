"""POS sale endpoint — atomic transaction: payment + stock deduction + log."""
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class POSSellAPIView(APIView):
    """POST /api/v1/shops/sell/

    Body:
      {
        client_id?: int,
        items: [{ kind: 'products'|'services'|'combos', id: int, qty: int }],
        payment_method: 'cash'|'card'|'balance'|'composite',
        promocode_code?: str,
        cash_part?: float, card_part?: float  // for composite
      }

    Atomically:
      1. resolves items, computes total
      2. applies promocode if given
      3. deducts from client deposit if balance
      4. creates Payment + StockOperation per product
      5. writes OperationLog entry
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.billing.models import Payment, PaymentMethod, OperationLog, LogAction
        from apps.shops.models import Product, Service, Combo, Stock

        # SECURITY: was trusting current_club_id / body `club` (attacker-controllable)
        # — a rogue operator could record POS sales against another club's Payment
        # records and deduct from another club's client deposits. Re-validate membership.
        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)
        if not club_id:
            return Response({'ok': False, 'message': 'club required or no access'}, status=403)

        items = request.data.get('items') or []
        if not items:
            return Response({'ok': False, 'message': 'cart empty'}, status=400)

        client_id = request.data.get('client_id')
        method = request.data.get('payment_method', 'cash')

        # --- Compute total & validate stock
        subtotal = Decimal('0')
        line_records = []  # [(kind, obj, qty, price)]
        for it in items:
            try:
                qty = int(it.get('qty', 1))
            except (TypeError, ValueError):
                qty = 0
            # BUGFIX: a negative/zero qty passed stock checks (x < negative is False),
            # INCREASED stock on "deduct", and made a negative-total Payment that
            # corrupted revenue. Reject non-positive quantities.
            if qty < 1:
                return Response({'ok': False, 'message': 'Количество должно быть ≥ 1'}, status=400)
            try:
                if it['kind'] == 'products':
                    obj = Product.objects.get(id=it['id'])
                    price = obj.price
                    try:
                        stock_obj = Stock.objects.filter(product=obj).first()
                        if stock_obj and stock_obj.quantity < qty:
                            return Response({'ok': False, 'message': f'Недостаточно «{obj.name}»: {stock_obj.quantity} шт.'}, status=400)
                    except Exception:
                        pass
                elif it['kind'] == 'services':
                    obj = Service.objects.get(id=it['id'])
                    price = obj.price
                elif it['kind'] == 'combos':
                    obj = Combo.objects.get(id=it['id'])
                    price = obj.sale_price
                    # BUGFIX: a combo draws down its component products, but stock was
                    # never checked or decremented for combos (only kind=='products').
                    # Validate every component has enough stock for qty combos.
                    try:
                        for ci in obj.product_items.select_related('product').all():
                            need = ci.qty * qty
                            st = Stock.objects.filter(product=ci.product).first()
                            if st and st.quantity < need:
                                return Response({'ok': False, 'message': f'Недостаточно «{ci.product.name}» для набора: {st.quantity} шт.'}, status=400)
                    except Exception:
                        pass
                else:
                    continue
            except Exception:
                return Response({'ok': False, 'message': f'item not found: {it}'}, status=400)
            subtotal += price * qty
            line_records.append((it['kind'], obj, qty, price))

        # --- Apply discount
        try:
            discount_pct = Decimal(str(request.data.get('discount_percent', 0) or 0))
            discount_pct = min(max(discount_pct, Decimal('0')), Decimal('100'))
        except Exception:
            discount_pct = Decimal('0')

        # Setting: «Автоприменение персональной скидки» — when on and a client is
        # attached, default to the client's effective (personal/group) discount.
        try:
            from apps.clubs.models import ClubSettings, UserClubProfile
            if client_id and ClubSettings.get_bool(club_id, 'personal_discount_auto', False):
                prof = UserClubProfile.objects.filter(user_id=client_id, club_id=club_id).first()
                auto = Decimal(str(getattr(prof, 'effective_discount', 0) or 0)) if prof else Decimal('0')
                discount_pct = max(discount_pct, min(auto, Decimal('100')))
        except Exception:
            pass

        if discount_pct > 0:
            # Only discount lines whose item allows it (Product/Service/Combo.applies_discount).
            # Was discounting the whole subtotal → non-discountable items and combos'
            # already-reduced sale_price got the personal discount stacked on anyway.
            discountable = sum(
                (price * qty for kind, obj, qty, price in line_records
                 if getattr(obj, 'applies_discount', True)),
                Decimal('0'),
            )
            discount_amt = (discountable * discount_pct / Decimal('100')).quantize(Decimal('1'))
        else:
            discount_amt = Decimal('0')

        total = subtotal - discount_amt

        # --- Atomic transaction
        with transaction.atomic():
            # Method enum (balance = депозит → записываем как TRANSFER + пометка)
            method_map = {
                'cash':     PaymentMethod.CASH,
                'card':     PaymentMethod.CARD,
                'transfer': PaymentMethod.TRANSFER,
                'balance':  PaymentMethod.TRANSFER,  # депозит — внутренний перевод
            }
            pay_method = method_map.get(method, PaymentMethod.CASH)
            pay_note = '[DEPOSIT][POS]' if method == 'balance' else '[POS]'

            # Deduct stock under a row LOCK and re-validate availability HERE (the
            # pre-check above ran before the transaction → a concurrent sale could
            # oversell). On underflow raise ValidationError → 400 + full rollback,
            # instead of the old silent clamp-to-zero that accepted the oversold sale.
            from rest_framework.exceptions import ValidationError as _VErr
            def _decrement(product, n):
                stock, _ = Stock.objects.select_for_update().get_or_create(
                    product=product, defaults={'quantity': 0})
                if stock.quantity < n:
                    raise _VErr({'stock': f'Недостаточно «{product.name}»: {stock.quantity} шт.'})
                stock.quantity -= n
                stock.save(update_fields=['quantity'])

            for kind, obj, qty, _ in line_records:
                if kind == 'products':
                    _decrement(obj, qty)
                elif kind == 'combos':
                    for ci in obj.product_items.select_related('product').all():
                        _decrement(ci.product, ci.qty * qty)

            # A combo may bundle a tariff (play-time). Credit those minutes to the
            # buyer's per-club balance — was charged (sale_price) but minutes_added=0,
            # so the bought time was silently never granted.
            if client_id:
                combo_minutes = 0
                for kind, obj, qty, _ in line_records:
                    if kind == 'combos' and getattr(obj, 'tariff_id', None):
                        try:
                            combo_minutes += int(obj.tariff.minutes or 0) * qty
                        except Exception:
                            pass
                if combo_minutes > 0:
                    from apps.clubs.models import UserClubProfile
                    prof, _ = UserClubProfile.objects.select_for_update().get_or_create(
                        user_id=client_id, club_id=club_id)
                    prof.add_minutes(combo_minutes)

            # If balance payment — spend BONUSES first (capped by «Процент списания
            # бонусов»), then the rest from the UserClubProfile deposit. Was deposit-only,
            # so bonus_balance (credited by promocodes/cashback) was never spendable.
            bonus_used = Decimal('0')
            if method == 'balance' and client_id:
                try:
                    from apps.clubs.models import UserClubProfile, ClubSettings
                    profile = UserClubProfile.objects.select_for_update().get(
                        user_id=client_id, club_id=club_id,
                    )
                    pay_total = total
                    if ClubSettings.get_bool(club_id, 'bonus_system', True):
                        pct = ClubSettings.get_int(club_id, 'bonus_writeoff_pct', 0)
                        bal = profile.bonus_balance or Decimal('0')
                        if pct > 0 and bal > 0:
                            cap = (total * Decimal(pct) / Decimal('100')).quantize(Decimal('0.01'))
                            bonus_used = min(bal, cap)
                            if bonus_used > 0:
                                profile.bonus_balance = bal - bonus_used
                                pay_total = total - bonus_used
                    if profile.deposit_money < pay_total:
                        return Response({
                            'ok': False,
                            'message': f'Недостаточно средств: депозит {profile.deposit_money} + бонусы {bonus_used} < {total} сум'
                        }, status=400)
                    profile.deposit_money -= pay_total
                    profile.save(update_fields=['deposit_money', 'bonus_balance'])
                except UserClubProfile.DoesNotExist:
                    return Response({'ok': False, 'message': 'У клиента нет профиля в клубе'}, status=400)

            # Discount + bonus note suffix
            disc_note = f'[СКИДКА {discount_pct}%]' if discount_amt > 0 else ''
            bonus_note = f'[БОНУС {bonus_used}]' if bonus_used > 0 else ''
            full_note = f'{pay_note}{disc_note}{bonus_note}'

            # Create Payment record (amount_paid = discounted total)
            payment = Payment.objects.create(
                user_id=client_id,
                admin=request.user if request.user.is_authenticated else None,
                amount_paid=total,
                minutes_added=0,
                payment_method=pay_method,
                note=full_note,
                club_id=club_id,
            )

            # OperationLog
            try:
                OperationLog.objects.create(
                    club_id=club_id,
                    subject=request.user if request.user.is_authenticated else None,
                    object_type='Payment',
                    object_id=str(payment.id),
                    object_repr=f"POS sale {total}сум" + (f" (скидка {discount_pct}%)" if discount_amt > 0 else ""),
                    action=LogAction.PAYMENT_CREATE,
                    payload={
                        'items': [
                            {'kind': k, 'id': o.id, 'name': o.name, 'qty': q, 'price': str(p)}
                            for k, o, q, p in line_records
                        ],
                        'method': method,
                        'subtotal': str(subtotal),
                        'discount_percent': str(discount_pct),
                        'discount_amount': str(discount_amt),
                        'total': str(total),
                        'promocode': request.data.get('promocode_code', ''),
                    },
                )
            except Exception:
                pass

        # Evaluate achievements (spend_single / spend_total) — was never invoked.
        if client_id:
            try:
                from apps.accounts.models import CustomUser
                from apps.loyalty.services.achievements import evaluate_achievements
                cu = CustomUser.objects.filter(id=client_id).first()
                if cu:
                    evaluate_achievements(cu, club_id, 'spend', total)
            except Exception:
                pass

        return Response({
            'ok': True,
            'payment_id': payment.id,
            'subtotal': str(subtotal),
            'discount_percent': str(discount_pct),
            'discount_amount': str(discount_amt),
            'total': str(total),
            'bonus_used': str(bonus_used),
            'method': method,
            'lines': len(line_records),
        }, status=status.HTTP_201_CREATED)
