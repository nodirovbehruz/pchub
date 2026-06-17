from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.api.v1.serializers.billing import (
    BalanceResponseSerializer,
    TariffPlanCreateSerializer,
    TariffPlanSerializer,
    TopUpSerializer,
)
from apps.billing.models import TariffPlan
from apps.billing.services.implementation.billing import BillingService

service = BillingService()


class UserListWithBalanceAPIView(APIView):
    """Admin: list all users with their current balance.
    Supports ?search=<q> and ?club=<id> filters.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import CustomUser
        from apps.billing.models import UserBalance
        from django.db.models import Q

        search = request.query_params.get("search", "").strip()
        club_id = getattr(request, "current_club_id", None) or request.query_params.get("club")

        qs = CustomUser.objects.filter(user_type="user").order_by("username")

        # Build club profile map for per-club discount/block data
        profile_map = {}
        if club_id:
            try:
                from apps.clubs.models import UserClubProfile
                profiles = UserClubProfile.objects.filter(club_id=club_id).select_related("user", "group")
                for p in profiles:
                    profile_map[p.user_id] = p
            except Exception:
                pass

        group_filter = request.query_params.get("group")  # filter by client group id

        if search:
            # POS cashier search: find ANY registered client (not restricted to club members)
            phone_q = search.lstrip('+')
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
                | Q(phone__icontains='+' + phone_q)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        elif club_id:
            # Clients list page: show ONLY members of this specific club
            member_ids = set(profile_map.keys())
            if group_filter:
                member_ids = {uid for uid, p in profile_map.items()
                              if str(getattr(p, "group_id", None)) == str(group_filter)}
            qs = qs.filter(id__in=member_ids)

        result = []
        for u in qs[:200]:  # limit for performance
            try:
                bal = UserBalance.objects.get(user=u)
            except UserBalance.DoesNotExist:
                bal = None
            profile = profile_map.get(u.pk)
            # Per-club deposit/bonus prefer profile; fall back to balance
            deposit_val = profile.deposit_money if (profile and profile.deposit_money) else getattr(bal, "deposit_money", 0)
            bonus_val = profile.bonus_balance if (profile and profile.bonus_balance) else getattr(bal, "bonus_balance", 0)
            # Postpaid holder: per-club profile when it's actually in postpaid mode,
            # else fall back to the global balance.
            ph = profile if (profile and getattr(profile, "session_mode", "prepaid") == "postpaid") else (bal or profile)
            reg = getattr(u, "created_at", None) or getattr(u, "date_joined", None)
            # Postpaid minutes/amount: bill the SAME wall-clock-max the close path uses
            # (max(counter, elapsed since started)). The raw counter only advances on
            # per-minute pings, so a dropped/late shell made the operator quote LESS
            # than the Payment that gets booked. Report the authoritative figure.
            pp_minutes = getattr(ph, "postpaid_minutes", 0) or 0
            pp_amount = getattr(ph, "postpaid_amount_due", 0) or 0
            if ph is not None and getattr(ph, "session_mode", "prepaid") == "postpaid":
                try:
                    from decimal import Decimal as _D
                    pp_minutes = service._postpaid_elapsed_minutes(ph)
                    pp_amount = ((_D(str(getattr(ph, "postpaid_rate", 0) or 0)) * _D(pp_minutes) / _D("60"))
                                 .quantize(_D("0.01")))
                except Exception:
                    pp_minutes = getattr(ph, "postpaid_minutes", 0) or 0
                    pp_amount = getattr(ph, "postpaid_amount_due", 0) or 0
            result.append({
                "id": str(u.pk),
                "username": u.username,
                "phone": str(getattr(u, "phone", None) or "") if getattr(u, "phone", None) else "",
                "email": u.email or "",
                "full_name": f"{u.first_name} {u.last_name}".strip() or "",
                "minutes_remaining": bal.minutes_remaining if bal else 0,
                "formatted_time": bal.formatted_time if bal else "0ч 0м",
                "is_active": (bal.is_active if bal else False),
                "deposit_money": str(deposit_val or 0),
                "bonus_balance": str(bonus_val or 0),
                # Per-club profile fields
                "personal_discount": profile.personal_discount if profile else 0,
                "is_blocked": profile.is_blocked if profile else False,
                "comment": profile.comment if profile else "",
                "group_id": getattr(profile, "group_id", None) if profile else None,
                "group_name": (profile.group.name if (profile and profile.group) else None),
                "effective_discount": (profile.effective_discount if profile else 0),
                "registered_at": reg.isoformat() if reg else None,
                "last_visit_at": (profile.last_visit_at.isoformat() if (profile and profile.last_visit_at) else None),
                # Postpaid fields — admin postpaid lives on the PER-CLUB profile, so
                # read from it first (was reading global UserBalance → status/Close
                # button never showed and the Close modal showed 0 min / 0 сум).
                "session_mode": getattr(ph, "session_mode", "prepaid") or "prepaid",
                "postpaid_minutes": pp_minutes,
                "postpaid_rate": str(getattr(ph, "postpaid_rate", 0) or 0),
                "postpaid_amount_due": str(pp_amount),
                "postpaid_started_at": (ph.postpaid_started_at.isoformat()
                                        if getattr(ph, "postpaid_started_at", None) else None),
            })
        return Response(result)


class UserClubProfilePatchAPIView(APIView):
    """Admin: update per-club client profile fields (discount, block, comment)."""

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, user_id):
        from apps.clubs.models import UserClubProfile
        from apps.clubs.api.v1.mixins import validated_club_id
        # SECURITY: was trusting current_club_id / body / query (attacker-controllable)
        # → could set personal_discount=100 / unblock on ANY club's client. Membership-checked.
        club_id = validated_club_id(request)
        if not club_id:
            return Response({"error": "club required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            profile = UserClubProfile.objects.get(user_id=user_id, club_id=club_id)
        except UserClubProfile.DoesNotExist:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

        allowed = {"personal_discount", "is_blocked", "comment"}
        update_fields = []
        for field in allowed:
            if field in request.data:
                val = request.data[field]
                if field == "personal_discount":
                    # Clamp 0..100 — was stored unchecked, and a value >100 makes
                    # ClientBuyTariff compute a NEGATIVE price (deposit increases, free
                    # minutes, negative Payment poisons revenue). Hard-bound it here.
                    try:
                        val = max(0, min(100, int(val)))
                    except (TypeError, ValueError):
                        return Response({"error": "personal_discount должен быть 0..100"},
                                        status=status.HTTP_400_BAD_REQUEST)
                setattr(profile, field, val)
                update_fields.append(field)
        if update_fields:
            profile.save(update_fields=update_fields)
        return Response({
            "id": str(profile.user_id),
            "personal_discount": profile.personal_discount,
            "is_blocked": profile.is_blocked,
            "comment": profile.comment,
        })


class TopUpAPIView(APIView):
    """Admin: add time to a user's balance."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TopUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # SECURITY: was trusting current_club_id / body `club` (attacker-controllable)
        # — any user with a valid JWT could topup against a foreign club's records.
        # Now re-validate membership via validated_club_id.
        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)
        if not club_id:
            return Response({"error": "Нет доступа к клубу"}, status=status.HTTP_403_FORBIDDEN)
        try:
            result = service.topup_user(
                user_id=serializer.validated_data["user_id"],
                minutes=serializer.validated_data["minutes"],
                amount_paid=serializer.validated_data["amount_paid"],
                payment_method=serializer.validated_data["payment_method"],
                admin=request.user,
                note=serializer.validated_data.get("note", ""),
                club_id=club_id,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        user_id = serializer.validated_data['user_id']
        from apps.accounts.models import CustomUser
        try:
            client = CustomUser.objects.get(pk=user_id)
            client_name = client.username
        except Exception:
            client = None
            client_name = str(user_id)

        # Audit log
        try:
            from apps.billing.models import OperationLog, LogAction
            OperationLog.objects.create(
                club_id=club_id, subject=request.user,
                object_type="UserClubProfile", object_id=str(user_id),
                object_repr=f"Пополнение: {client_name}",
                action=LogAction.DEPOSIT_TOPUP,
                payload={
                    "amount": str(serializer.validated_data['amount_paid']),
                    "method": serializer.validated_data['payment_method'],
                    "client": client_name,
                },
            )
        except Exception:
            pass

        # Telegram notification
        try:
            from apps.clubs.services.telegram import notify_club
            method_labels = {'cash': '💵 Наличные', 'card': '💳 Карта', 'transfer': '📲 Перевод', 'deposit': '🏦 Депозит'}
            method_label = method_labels.get(serializer.validated_data['payment_method'], serializer.validated_data['payment_method'])
            notify_club(club_id, (
                f"💰 <b>Пополнение депозита</b>\n"
                f"👤 Клиент: {client_name}\n"
                f"💵 Сумма: {serializer.validated_data['amount_paid']} сум\n"
                f"💳 Способ: {method_label}"
            ))
        except Exception:
            pass

        return Response(result, status=status.HTTP_201_CREATED)


class MyBalanceAPIView(APIView):
    """Client app: check own balance (identified by JWT token)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        club_id = getattr(request, "current_club_id", None) or request.query_params.get("club")
        result = service.check_user_access(request.user, club_id=club_id)
        return Response(result)


class ClientTariffsAPIView(APIView):
    """Client app: list available tariffs for the current club."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.billing.models import TariffPlan
        from apps.billing.api.v1.serializers.billing import TariffPlanSerializer

        club_id = getattr(request, "current_club_id", None) or request.query_params.get("club")
        qs = TariffPlan.objects.filter(is_active=True).prefetch_related("prices")
        if club_id:
            qs = qs.filter(club_id=club_id)
        qs = qs.order_by("tariff_type", "price")
        return Response(TariffPlanSerializer(qs, many=True).data)


class ClientBuyTariffAPIView(APIView):
    """Client app: purchase a tariff using club deposit.

    POST body: { tariff_id: int, club?: int }
    Deducts tariff.price from UserClubProfile.deposit_money,
    adds tariff.minutes to UserBalance, creates a Payment record.
    Returns: { success, minutes_added, minutes_remaining, formatted_time, deposit_remaining }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from decimal import Decimal
        from django.db import transaction

        from apps.billing.models import TariffPlan, UserBalance, Payment

        tariff_id = request.data.get("tariff_id")
        club_id = getattr(request, "current_club_id", None) or request.data.get("club")

        if not tariff_id:
            return Response({"error": "tariff_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tariff = TariffPlan.objects.get(pk=tariff_id, is_active=True)
        except TariffPlan.DoesNotExist:
            return Response({"error": "Тариф не найден"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        price = tariff.price

        # BUGFIX: resolve the per-zone / day-night price the SAME way the operator path
        # (AdminSessionStart) does, keyed off the client's PC — so a tariff costs the
        # same whether the client self-buys in the shell or the operator seats them.
        # Was always charging the flat base price (VIP/night mispriced). The shell now
        # sends computer_id; fall back to the user's active_hardware_id PC.
        try:
            from apps.billing.models import PricePeriod
            from apps.computers.models import Computer
            pc = None
            cid = request.data.get("computer_id")
            if cid:
                pc = Computer.objects.filter(id=cid).first()
            if pc is None and getattr(user, "active_hardware_id", ""):
                pc = Computer.objects.filter(hardware_id=user.active_hardware_id).first()
            if pc is not None and pc.group_id:
                from django.utils import timezone as _tz
                now = _tz.localtime()
                period = PricePeriod.NIGHT if (now.hour >= 22 or now.hour < 8) else PricePeriod.DAY
                try:
                    from apps.clubs.models import ClubSettings
                    if ClubSettings.get_bool(pc.club_id, "holiday_tariff", False):
                        hd = ClubSettings.get_value(pc.club_id, "holiday_dates", []) or []
                        if now.strftime("%d.%m") in hd or now.strftime("%d.%m.%Y") in hd:
                            period = PricePeriod.NIGHT
                except Exception:
                    pass
                tp = (tariff.prices.filter(group_id=pc.group_id, period=period).first()
                      or tariff.prices.filter(group_id=pc.group_id).first())
                if tp:
                    price = tp.price
        except Exception:
            pass

        # Fetch per-club deposit
        with transaction.atomic():
            # Lock + read deposit + check + deduct ALL inside the transaction.
            # (select_for_update is a no-op outside atomic → was a double-spend race.)
            profile = None
            deposit = Decimal("0")
            if club_id:
                try:
                    from apps.clubs.models import UserClubProfile
                    profile = UserClubProfile.objects.select_for_update().get(user=user, club_id=club_id)
                    deposit = profile.deposit_money
                except Exception:
                    profile = None

            # H2: apply the client's personal/group discount (effective_discount) —
            # the operator seat path honors discounts but client self-buy charged full
            # price. Gated by the tariff's apply_discount flag.
            if profile is not None and getattr(tariff, "apply_discount", True):
                try:
                    disc = Decimal(str(getattr(profile, "effective_discount", 0) or 0))
                    if disc > 0:
                        price = (price * (Decimal("100") - disc) / Decimal("100")).quantize(Decimal("0.01"))
                except Exception:
                    pass

            # Spend BONUSES first toward the price (gated by «Оплата тарифов бонусами»
            # + capped by «Процент списания бонусов»), then deposit covers the rest.
            # Was deposit-only → bonus_balance was never spendable on tariffs.
            bonus_used = Decimal("0")
            if profile and club_id:
                try:
                    from apps.clubs.models import ClubSettings
                    if (ClubSettings.get_bool(club_id, "bonus_system", True)
                            and ClubSettings.get_bool(club_id, "bonus_pay_tariffs", False)):
                        # Clamp 0..100 — an unbounded pct made `cap` exceed the price, so
                        # bonus_used > price → price_from_deposit went negative → the buy
                        # INCREASED the client's deposit (free money).
                        pct = max(0, min(100, ClubSettings.get_int(club_id, "bonus_writeoff_pct", 0)))
                        bal = profile.bonus_balance or Decimal("0")
                        if pct > 0 and bal > 0:
                            cap = (price * Decimal(pct) / Decimal("100")).quantize(Decimal("0.01"))
                            bonus_used = min(bal, cap)
                except Exception:
                    bonus_used = Decimal("0")
            price_from_deposit = price - bonus_used

            if deposit < price_from_deposit:
                missing = float(price_from_deposit - deposit)
                return Response({
                    "error": "Недостаточно средств на депозите",
                    "missing": round(missing, 2),
                    "deposit": str(deposit),
                    "price": str(price),
                }, status=status.HTTP_400_BAD_REQUEST)

            # Deduct from deposit (+ bonus) and credit TIME to this club (per-club minutes).
            if profile:
                profile.deposit_money = deposit - price_from_deposit
                if bonus_used > 0:
                    profile.bonus_balance = (profile.bonus_balance or Decimal("0")) - bonus_used
                profile.add_minutes(tariff.minutes)  # also saves is_active + minutes
                profile.save(update_fields=["deposit_money", "bonus_balance"])
                holder = profile
            else:
                # No club context — legacy global fallback.
                holder, _ = UserBalance.objects.get_or_create(user=user)
                holder.add_minutes(tariff.minutes)

            # Audit record
            Payment.objects.create(
                user=user,
                admin=None,
                amount_paid=price,
                minutes_added=tariff.minutes,
                payment_method="deposit",
                note=f"[CLIENT] Тариф: {tariff.name}" + (f" [БОНУС {bonus_used}]" if bonus_used > 0 else ""),
                club_id=club_id,
            )

        return Response({
            "success": True,
            "tariff_name": tariff.name,
            "minutes_added": tariff.minutes,
            "minutes_remaining": holder.minutes_remaining,
            "formatted_time": holder.formatted_time,
            "deposit_remaining": str(profile.deposit_money if profile else "0"),
        })


class DeductMinuteAPIView(APIView):
    """Client app: deduct one minute from user's balance."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        club_id = getattr(request, "current_club_id", None) or request.data.get("club")
        result = service.deduct_minute_user(request.user, club_id=club_id)
        return Response(result)


class MySessionAPIView(APIView):
    """Client app: full session + payment history for the logged-in user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        club_id = getattr(request, "current_club_id", None) or request.query_params.get("club")
        try:
            result = service.get_my_session_user(request.user, club_id=club_id)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)


class MyVisitsAPIView(APIView):
    """Client app: monthly visit dynamics for the logged-in user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.utils import timezone

        try:
            year = int(request.query_params.get("year", timezone.now().year))
        except (TypeError, ValueError):
            return Response({"error": "year должен быть числом"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = service.get_my_visits_user(request.user, year)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        return Response(result)


class PaymentListAPIView(APIView):
    """Admin: list all payments, optionally filtered by user or club."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.billing.models import Payment

        user_id = request.query_params.get("user_id")
        # SECURITY: was trusting current_club_id / ?club= (attacker-controllable) so
        # any authenticated user could read another club's full payment history.
        # Platform admins may pass ?club= freely; others are scoped to their club.
        from apps.clubs.api.v1.mixins import validated_club_id
        is_platform_admin = getattr(request.user, "user_type", "") == "admin"
        if is_platform_admin:
            club_id = getattr(request, "current_club_id", None) or request.query_params.get("club")
        else:
            club_id = validated_club_id(request)

        qs = Payment.objects.select_related("user", "admin").order_by("-created_at")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if club_id:
            qs = qs.filter(club_id=club_id)
        elif not is_platform_admin:
            # No authorized club → return nothing rather than leaking all payments.
            return Response([])

        rows = list(qs[:500].values(
            "id", "user__id", "user__username", "admin__username",
            "amount_paid", "minutes_added", "payment_method", "note", "created_at",
        ))
        for row in rows:
            row["user_id"]        = row.pop("user__id", None)
            row["user_username"]  = row.pop("user__username", None)
            row["admin_username"] = row.pop("admin__username", None)
        return Response(rows)


class PaymentRefundAPIView(APIView):
    """Admin: refund a payment.

    For POS sales ([POS] in note):
      - Restores product stock from OperationLog payload
      - Returns amount to user's club deposit if paid by deposit ([DEPOSIT][POS])
    For billing/time payments:
      - Reverses minutes_added from user balance
    Always marks note with [REFUNDED] and writes OperationLog entry.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from decimal import Decimal

        from django.db import transaction

        from apps.billing.models import (
            OperationLog, LogAction, Payment, UserBalance,
        )

        try:
            payment = Payment.objects.select_related("user").get(pk=pk)
        except Payment.DoesNotExist:
            return Response({"error": "Платёж не найден"}, status=status.HTTP_404_NOT_FOUND)

        # SECURITY: refunds move cash — verify the operator manages the PAYMENT's club
        # (was any authenticated user → cross-club refund / register drain).
        ref_club = getattr(payment, "club_id", None)
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            ok = bool(ref_club) and (Club.objects.filter(id=ref_club, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=ref_club, is_active=True, role__in=["owner", "manager", "operator"]
            ).exists())
            if not ok:
                return Response({"error": "Нет прав на возврат этого платежа"}, status=status.HTTP_403_FORBIDDEN)

        if payment.note and "[REFUNDED]" in payment.note:
            return Response({"error": "Платёж уже возвращён"}, status=status.HTTP_400_BAD_REQUEST)

        # Settings gate: «Отмена платежей» + «Период отмены (мин)».
        from apps.clubs.models import ClubSettings
        if not ClubSettings.get_bool(ref_club, "allow_payment_cancel", True):
            return Response({"error": "Отмена платежей отключена в настройках клуба"},
                            status=status.HTTP_403_FORBIDDEN)
        window = ClubSettings.get_int(ref_club, "cancel_period_min", 0)
        if window and payment.created_at:
            from django.utils import timezone
            age_min = (timezone.now() - payment.created_at).total_seconds() / 60
            if age_min > window:
                return Response(
                    {"error": f"Период отмены истёк ({window} мин). Платёж нельзя вернуть."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        note = payment.note or ""
        is_pos = "[POS]" in note
        is_deposit_pos = "[DEPOSIT]" in note and is_pos

        details = {}  # returned to caller

        with transaction.atomic():
            # Idempotency: the [REFUNDED] check above is unlocked, so two concurrent
            # refund requests for the same payment could BOTH pass it and reverse
            # stock/deposit + cut a cash-out (РКО) twice. Re-fetch under a row lock and
            # re-check the stamp before doing any reversal.
            payment = Payment.objects.select_for_update().select_related("user").get(pk=pk)
            if payment.note and "[REFUNDED]" in payment.note:
                return Response({"error": "Платёж уже возвращён"}, status=status.HTTP_400_BAD_REQUEST)

            if is_pos:
                # ── POS sale refund ──────────────────────────────────────────
                # 1. Find the OperationLog entry that recorded this sale
                log_entry = OperationLog.objects.filter(
                    object_type="Payment",
                    object_id=str(payment.id),
                    action=LogAction.PAYMENT_CREATE,
                ).first()

                restored_items = []
                if log_entry and log_entry.payload.get("items"):
                    from apps.shops.models import Stock, Product
                    from django.db.models import F

                    for item in log_entry.payload["items"]:
                        if item.get("kind") == "products":
                            try:
                                product = Product.objects.get(id=item["id"])
                                stock, _ = Stock.objects.get_or_create(
                                    product=product, defaults={"quantity": 0}
                                )
                                qty = int(item.get("qty", 1))
                                Stock.objects.filter(pk=stock.pk).update(
                                    quantity=F("quantity") + qty
                                )
                                restored_items.append({
                                    "product_id": item["id"],
                                    "name": item.get("name", ""),
                                    "qty": qty,
                                })
                            except Exception:
                                pass  # best-effort stock restore

                details["restored_stock"] = restored_items

                # 2. Return deposit money (+ bonuses) if paid from balance
                if is_deposit_pos and payment.user:
                    try:
                        from apps.clubs.models import UserClubProfile
                        from decimal import Decimal as _D
                        import re as _re

                        # M4: club from the PAYMENT (authoritative), never trust body.
                        club_id = payment.club_id or (log_entry.club_id if log_entry else None)
                        if club_id:
                            profile = UserClubProfile.objects.select_for_update().get(
                                user=payment.user, club_id=club_id
                            )
                            profile.deposit_money = profile.deposit_money + payment.amount_paid
                            upd = ["deposit_money"]
                            # M6: restore bonuses that were spent on this sale ([БОНУС N]).
                            m = _re.search(r"\[БОНУС\s+([0-9.]+)\]", note)
                            if m:
                                try:
                                    bb = _D(m.group(1))
                                    profile.bonus_balance = (profile.bonus_balance or _D("0")) + bb
                                    upd.append("bonus_balance")
                                    details["bonus_returned"] = str(bb)
                                except Exception:
                                    pass
                            profile.save(update_fields=upd)
                            details["deposit_returned"] = str(payment.amount_paid)
                    except Exception:
                        pass  # best-effort deposit restore

            else:
                # ── Billing / time payment refund ────────────────────────────
                from decimal import Decimal as _D
                import re as _re
                refund_club = payment.club_id
                profile = None
                if payment.user and refund_club:
                    try:
                        from apps.clubs.models import UserClubProfile
                        profile = UserClubProfile.objects.select_for_update().filter(
                            user=payment.user, club_id=refund_club).first()
                    except Exception:
                        profile = None

                # C1: reclaim the purchased minutes from the PER-CLUB ledger the shell
                # reads (was deducting the legacy global UserBalance → time never
                # reclaimed, client kept the time while money was returned).
                # Skip postpaid bills: a [POSTPAID] payment records minutes PLAYED on
                # credit (never added to minutes_remaining), so reversing them here would
                # destroy unrelated prepaid time the client actually bought.
                if payment.user and payment.minutes_added > 0 and "[POSTPAID]" not in (payment.note or ""):
                    try:
                        holder = profile or UserBalance.objects.get_or_create(user=payment.user)[0]
                        holder.minutes_remaining = max(0, (holder.minutes_remaining or 0) - payment.minutes_added)
                        holder.is_active = holder.minutes_remaining > 0
                        fields = ["minutes_remaining", "is_active"]
                        if hasattr(holder, "last_updated"):
                            fields.append("last_updated")
                        holder.save(update_fields=fields)
                        details["minutes_reversed"] = payment.minutes_added
                    except Exception:
                        pass

                # If paid from deposit (client buy-tariff), return the deposit (+ any
                # bonus spent). No РКО fires for 'deposit' so this is the only refund path.
                if profile is not None and payment.payment_method == "deposit" and payment.amount_paid:
                    try:
                        # The sale spent (amount_paid - bonus_used) from deposit and
                        # bonus_used from bonuses. Return EACH part to its own bucket —
                        # was crediting the FULL amount_paid to deposit AND the bonus back,
                        # over-refunding by bonus_used (free money).
                        bb = _D("0")
                        m = _re.search(r"\[БОНУС\s+([0-9.]+)\]", note)
                        if m:
                            try:
                                bb = _D(m.group(1))
                            except Exception:
                                bb = _D("0")
                        deposit_return = payment.amount_paid - bb
                        if deposit_return < 0:
                            deposit_return = _D("0")
                        profile.deposit_money = (profile.deposit_money or _D("0")) + deposit_return
                        upd = ["deposit_money"]
                        if bb > 0:
                            profile.bonus_balance = (profile.bonus_balance or _D("0")) + bb
                            upd.append("bonus_balance")
                            details["bonus_returned"] = str(bb)
                        profile.save(update_fields=upd)
                        details["deposit_returned"] = str(deposit_return)
                    except Exception:
                        pass

                # A cash/card DEPOSIT TOP-UP credited deposit_money (+ cashback) at
                # top-up time; refunding it (the РКО below returns the cash) must DEBIT
                # that deposit back — else the client keeps free balance. POS sales are
                # handled in the is_pos branch; postpaid never credits deposit.
                # Key off the [TOPUP] marker, NOT minutes_added==0 — a COMBINED time+money
                # topup credited the deposit too but has minutes>0, so the old gate skipped
                # it and the client kept the deposit on refund (free money). The marker
                # also excludes session-start cash payments (minutes>0, no deposit credit).
                # Key off the [TOPUP] marker, NOT minutes_added==0 — a COMBINED time+money
                # topup credited the deposit too but has minutes>0, so the old gate skipped
                # it and the client kept the deposit on refund (free money). The marker
                # also excludes session-start cash payments (minutes>0, no deposit credit).
                elif (profile is not None and payment.payment_method in ("cash", "card")
                      and "[TOPUP]" in note
                      and "[POSTPAID]" not in note and payment.amount_paid):
                    try:
                        profile.deposit_money = max(_D("0"), (profile.deposit_money or _D("0")) - payment.amount_paid)
                        upd = ["deposit_money"]
                        try:
                            from apps.clubs.models import ClubSettings
                            if ClubSettings.get_bool(refund_club, "bonus_system", True):
                                from apps.loyalty.models import CashbackRule
                                from django.db.models import Q as _Q
                                # Match the valid_until filter used at CREDIT time, anchored
                                # to the topup moment — was missing, so an expired rule
                                # (no cashback ever credited) got reversed, destroying
                                # bonuses the client earned elsewhere.
                                _ref = payment.created_at
                                _q = (CashbackRule.objects.filter(
                                    club_id=refund_club, is_active=True,
                                    deposit_threshold__lte=payment.amount_paid))
                                if _ref:
                                    _q = _q.filter(_Q(valid_until__isnull=True) | _Q(valid_until__gte=_ref))
                                rule = _q.order_by("-deposit_threshold").first()
                                if rule:
                                    cb = rule.compute_reward(payment.amount_paid)
                                    if cb:
                                        profile.bonus_balance = max(_D("0"), (profile.bonus_balance or _D("0")) - cb)
                                        upd.append("bonus_balance")
                                        details["bonus_reversed"] = str(cb)
                        except Exception:
                            pass
                        profile.save(update_fields=upd)
                        details["deposit_debited"] = str(payment.amount_paid)
                    except Exception:
                        pass

            # Determine club for further steps — the PAYMENT's club is authoritative.
            club_id_for_log = payment.club_id or getattr(request, "current_club_id", None)

            # Auto-create РКО for cash/card refunds (money physically leaves the register)
            if payment.amount_paid and payment.payment_method in ("cash", "card") and club_id_for_log:
                try:
                    from apps.billing.models import CashOrder, CashOrderType, Shift

                    # M5: the РКО must hit THIS club's open shift, not the most-recently
                    # opened shift across all clubs (was no club filter → wrong drawer).
                    active_shift = (
                        Shift.objects.filter(is_active=True, club_id=club_id_for_log)
                        .order_by("-start_time")
                        .first()
                    )

                    if active_shift:
                        method_label = "наличными" if payment.payment_method == "cash" else "по карте"
                        CashOrder.objects.create(
                            club_id=club_id_for_log,
                            shift=active_shift,
                            admin=request.user if request.user.is_authenticated else None,
                            type=CashOrderType.OUTCOME,
                            amount=payment.amount_paid,
                            comment=f"Возврат платежа #{payment.id} ({method_label})[AUTO-REFUND]",
                        )
                        details["rko_created"] = True
                except Exception:
                    pass  # best-effort — refund still completes without RKO

            # Mark payment as refunded
            payment.note = f"[REFUNDED] {note}".strip()
            payment.save(update_fields=["note"])

            # Write audit log
            try:
                OperationLog.objects.create(
                    club_id=club_id_for_log,
                    subject=request.user if request.user.is_authenticated else None,
                    object_type="Payment",
                    object_id=str(payment.id),
                    object_repr=f"Возврат платежа #{payment.id} ({payment.amount_paid} сум)",
                    action=LogAction.PAYMENT_REFUND,
                    payload={
                        "original_payment_id": payment.id,
                        "amount": str(payment.amount_paid),
                        "is_pos": is_pos,
                        **details,
                    },
                )
            except Exception:
                pass

        return Response({
            "success": True,
            "payment_id": payment.id,
            "message": f"Платёж #{payment.id} возвращён",
            **details,
        })


class StartPostpaidAPIView(APIView):
    """Admin: start a postpaid session for a client.

    POST body: { user_id, rate_per_hour }
    The client's shell immediately gets has_access=true and plays on credit.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from decimal import Decimal, InvalidOperation

        user_id = request.data.get("user_id")
        raw_rate = request.data.get("rate_per_hour", 0)
        # SECURITY: was trusting current_club_id / body `club` — a rogue operator
        # could start a postpaid session against any club's client profile (IDOR).
        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)

        if not user_id:
            return Response({"error": "user_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rate = Decimal(str(raw_rate))
            if rate < 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            return Response({"error": "Некорректная ставка"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = service.start_postpaid_session(
                user_id=user_id,
                rate_per_hour=rate,
                admin=request.user,
                club_id=club_id,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ClosePostpaidAPIView(APIView):
    """Admin: close a postpaid session and collect payment.

    POST body: { user_id, payment_method }
    Calculates cost = postpaid_minutes / 60 × rate_per_hour,
    creates a Payment record, resets balance to prepaid/idle.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user_id = request.data.get("user_id")
        payment_method = request.data.get("payment_method", "cash")
        # SECURITY: was trusting current_club_id / body `club` — a rogue operator
        # could close (and bill) a postpaid session belonging to another club's client.
        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)

        if not user_id:
            return Response({"error": "user_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = service.close_postpaid_session(
                user_id=user_id,
                payment_method=payment_method,
                admin=request.user,
                club_id=club_id,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


def _resolve_computer(request):
    """Find the target Computer from computer_id or hardware_id in the request."""
    from apps.computers.models import Computer
    cid = request.data.get("computer_id") or request.query_params.get("computer_id")
    hw = request.data.get("hardware_id") or request.query_params.get("hardware_id")
    if cid:
        return Computer.objects.filter(pk=cid).first()
    if hw:
        return Computer.objects.filter(hardware_id=hw).first()
    return None


class GuestPostpaidStartAPIView(APIView):
    """Admin: start a WALK-IN guest postpaid session on a PC (no client account).

    POST body: { computer_id | hardware_id, rate_per_hour }
    The PC's guest account starts playing on credit immediately; the shell picks
    this up via the guest-status endpoint and auto-enters without a login.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from decimal import Decimal, InvalidOperation

        computer = _resolve_computer(request)
        if not computer:
            return Response({"error": "ПК не найден (computer_id/hardware_id)"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            rate = Decimal(str(request.data.get("rate_per_hour", 0)))
            if rate < 0:
                raise ValueError()
        except (InvalidOperation, ValueError):
            return Response({"error": "Некорректная ставка"}, status=status.HTTP_400_BAD_REQUEST)

        # SECURITY: was trusting current_club_id / body `club` — operator A could
        # start a guest postpaid session on club B's PC (IDOR + cross-club write).
        # Validate via membership, then confirm the resolved PC belongs to that club.
        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)
        if not club_id:
            # Fall back to the PC's own club so the shell (which sends computer_id but
            # no explicit club param) keeps working — but only if the user is a member.
            from apps.clubs.models import Club, ClubMembership
            u = request.user
            is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
            if is_platform_admin:
                club_id = computer.club_id
            elif computer.club_id and (
                Club.objects.filter(id=computer.club_id, owner=u).exists()
                or ClubMembership.objects.filter(user=u, club_id=computer.club_id, is_active=True,
                                                 role__in=["owner", "manager", "operator"]).exists()
            ):
                club_id = computer.club_id
            else:
                return Response({"error": "Нет доступа к клубу этого ПК"}, status=status.HTTP_403_FORBIDDEN)
        # Ensure the resolved PC actually belongs to the authorized club.
        if computer.club_id and computer.club_id != club_id:
            return Response({"error": "ПК не принадлежит вашему клубу"}, status=status.HTTP_403_FORBIDDEN)

        # Setting gate: «Постоплата» must be enabled for this club.
        from apps.clubs.models import ClubSettings
        if not ClubSettings.get_bool(club_id or computer.club_id, "postpayment", True):
            return Response(
                {"error": "Постоплата отключена в настройках клуба"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            result = service.start_guest_postpaid(
                computer=computer, rate_per_hour=rate, admin=request.user, club_id=club_id,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class GuestPostpaidCloseAPIView(APIView):
    """Admin: close a PC's guest postpaid session and bill the played minutes.

    POST body: { computer_id | hardware_id, payment_method }
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        computer = _resolve_computer(request)
        if not computer:
            return Response({"error": "ПК не найден"}, status=status.HTTP_400_BAD_REQUEST)
        payment_method = request.data.get("payment_method", "cash")
        # SECURITY: was trusting current_club_id / body `club` — operator A could
        # bill/close a guest session on club B's PC without being a member there.
        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)
        if not club_id:
            # Shell sends computer_id but no explicit club param — allow if the user
            # is a member of the PC's own club (operator closing via PC map).
            from apps.clubs.models import Club, ClubMembership
            u = request.user
            is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
            if is_platform_admin:
                club_id = computer.club_id
            elif computer.club_id and (
                Club.objects.filter(id=computer.club_id, owner=u).exists()
                or ClubMembership.objects.filter(user=u, club_id=computer.club_id, is_active=True,
                                                 role__in=["owner", "manager", "operator"]).exists()
            ):
                club_id = computer.club_id
            else:
                return Response({"error": "Нет доступа к клубу этого ПК"}, status=status.HTTP_403_FORBIDDEN)
        if computer.club_id and computer.club_id != club_id:
            return Response({"error": "ПК не принадлежит вашему клубу"}, status=status.HTTP_403_FORBIDDEN)
        try:
            result = service.close_guest_postpaid(
                computer=computer, payment_method=payment_method,
                admin=request.user, club_id=club_id,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class GuestStatusAPIView(APIView):
    """PC client (pre-login): is there an active guest postpaid session for this PC?

    GET ?hardware_id=<id>
    Returns { active, access_token, club_id, rate } so the shell can auto-enter
    guest mode without a login. Token is only issued while a session is active.
    """

    # Pre-login endpoint: must stay public. We DISABLE authentication entirely so
    # a stale/expired "Authorization: Bearer ..." header left in the shell's
    # HttpClient can't make JWTAuthentication raise 401 before AllowAny applies.
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "pc_register"

    def get(self, request):
        from apps.computers.models import Computer
        from apps.clubs.models import UserClubProfile
        from apps.accounts.models import CustomUser
        from rest_framework_simplejwt.tokens import RefreshToken

        hw = request.query_params.get("hardware_id")
        if not hw:
            return Response({"active": False})
        computer = Computer.objects.filter(hardware_id=hw).first()
        if not computer:
            return Response({"active": False})

        guest = CustomUser.objects.filter(username=f"guest-pc-{computer.id}").first()
        if not guest:
            return Response({"active": False})

        profile = UserClubProfile.objects.filter(
            user=guest, club_id=computer.club_id, is_guest=True,
            session_mode="postpaid", is_active=True,
        ).first()
        if not profile:
            return Response({"active": False})

        token = service.long_lived_token(guest)
        return Response({
            "active": True,
            "access_token": token,
            "club_id": computer.club_id,
            "rate": str(profile.postpaid_rate or 0),
            "postpaid_minutes": profile.postpaid_minutes,
        })


class AdminDashboardStatsAPIView(APIView):
    """Admin: aggregate statistics for the admin dashboard.

    SECURITY: this aggregates revenue across ALL clubs (no tenant scope in the
    service), so it must be platform-admin only — was leaking platform-wide revenue
    to any authenticated user. Per-club dashboards use DashboardStatsAPIView.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "user_type", "") != "admin":
            return Response({"error": "Только для платформенного администратора"},
                            status=status.HTTP_403_FORBIDDEN)
        data = service.get_admin_dashboard_stats()
        return Response(data)


class TariffPlanListAPIView(generics.ListCreateAPIView):
    """List + create tariff plans.

    GET: list active tariffs, optional ?club=<id> filter.
    POST: create new tariff (with optional nested prices).
    """

    serializer_class = TariffPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TariffPlan.objects.all().prefetch_related("prices")
        # Admin passes ?all=1 to see/re-enable INACTIVE tariffs (otherwise a disabled
        # tariff vanished from the panel and could never be reactivated). Default stays
        # active-only so the client shell never sees disabled tariffs.
        if self.request.query_params.get("all") not in ("1", "true", "yes"):
            qs = qs.filter(is_active=True)
        club_id = self.request.query_params.get("club")
        if club_id:
            qs = qs.filter(club_id=club_id)
        return qs.order_by("tariff_type", "price")

    def perform_create(self, serializer):
        # SECURITY: force the tariff into the authorized club — body `club` was
        # trusted, letting a member forge a near-zero tariff in another club.
        from apps.clubs.api.v1.mixins import validated_club_id
        from rest_framework.exceptions import PermissionDenied
        cid = validated_club_id(self.request)
        if not cid:
            raise PermissionDenied("Нет доступа к клубу")
        try:
            serializer.validated_data.pop("club", None)
        except Exception:
            pass
        tariff = serializer.save(club_id=cid)
        from apps.billing.services.audit import log_action
        from apps.billing.models import LogAction
        log_action(
            self.request, LogAction.DB_CREATE, obj=tariff, object_type="Tariff",
            club_id=getattr(tariff, "club_id", None),
            repr_=f"Тариф создан: {tariff.name}",
            payload={"name": tariff.name, "price": str(tariff.price), "minutes": tariff.minutes},
        )


class TariffPlanDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve / update / delete a tariff plan — tenant-scoped (IDOR fix)."""

    serializer_class = TariffPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = TariffPlan.objects.all().prefetch_related("prices")
    lookup_field = "pk"

    def get_queryset(self):
        # Scope to the authorized club so a foreign tariff id 404s (was editable/
        # deletable cross-club). Platform admins see all.
        from apps.clubs.api.v1.mixins import validated_club_id
        qs = TariffPlan.objects.all().prefetch_related("prices")
        if getattr(self.request.user, "user_type", "") == "admin":
            return qs
        cid = validated_club_id(self.request)
        return qs.filter(club_id=cid) if cid else qs.none()

    def perform_update(self, serializer):
        # Don't let `club` be reassigned to move/steal a tariff into another club.
        try:
            serializer.validated_data.pop("club", None)
        except Exception:
            pass
        tariff = serializer.save()
        from apps.billing.services.audit import log_action
        from apps.billing.models import LogAction
        log_action(
            self.request, LogAction.DB_UPDATE, obj=tariff, object_type="Tariff",
            club_id=getattr(tariff, "club_id", None),
            repr_=f"Тариф изменён: {tariff.name}",
            payload={"name": tariff.name, "price": str(tariff.price)},
        )

    def perform_destroy(self, instance):
        from apps.billing.services.audit import log_action
        from apps.billing.models import LogAction
        log_action(
            self.request, LogAction.DB_DELETE, obj=instance, object_type="Tariff",
            club_id=getattr(instance, "club_id", None),
            repr_=f"Тариф удалён: {instance.name}",
            payload={"name": instance.name},
        )
        instance.delete()


class TariffPlanCreateAPIView(APIView):
    """Legacy: kept for old frontend. Use POST /tariffs/ instead."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.clubs.api.v1.mixins import validated_club_id
        cid = validated_club_id(request)
        if not cid:
            return Response({"error": "Нет доступа к клубу"}, status=status.HTTP_403_FORBIDDEN)
        serializer = TariffPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("club", None)
        data.pop("club_id", None)
        tariff = TariffPlan.objects.create(club_id=cid, **data)
        return Response(
            TariffPlanSerializer(tariff).data, status=status.HTTP_201_CREATED
        )


class TariffPlanDeleteAPIView(APIView):
    """Legacy: kept for old frontend. Use DELETE /tariffs/<id>/ instead."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        from apps.clubs.api.v1.mixins import validated_club_id
        # SECURITY: scope to authorized club (was TariffPlan.objects.get(pk) →
        # any operator could delete ANY club's tariff by id).
        cid = validated_club_id(request)
        is_platform_admin = getattr(request.user, "is_admin", False) or getattr(request.user, "user_type", "") == "admin"
        try:
            qs = TariffPlan.objects.all() if is_platform_admin else TariffPlan.objects.filter(club_id=cid)
            tariff = qs.get(pk=pk)
            tariff.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TariffPlan.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
