from decimal import Decimal

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.loyalty.models import (
    Achievement, CashbackRule, Promocode, PromocodeRewardType,
    PromocodeUsage, UserAchievement,
)


class MyLoyaltyAPIView(APIView):
    """GET /api/v1/loyalty/my-summary/?club=<id>

    Client app: the logged-in user's loyalty snapshot for the current club —
    deposit, bonus balance, and the club's achievement catalogue with an
    `unlocked` flag for each. Read-only, scoped to the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        club_id = (
            getattr(request, "current_club_id", None)
            or request.META.get("HTTP_X_CLUB_ID")
            or request.query_params.get("club")
        )

        deposit = bonus = Decimal("0")
        try:
            from apps.clubs.models import UserClubProfile
            if club_id:
                profile = UserClubProfile.objects.filter(user=user, club_id=club_id).first()
                if profile:
                    deposit = profile.deposit_money or Decimal("0")
                    bonus = profile.bonus_balance or Decimal("0")
        except Exception:
            pass

        unlocked_ids = set(
            UserAchievement.objects.filter(user=user).values_list("achievement_id", flat=True)
        )
        ach_qs = Achievement.objects.filter(is_active=True)
        if club_id:
            ach_qs = ach_qs.filter(club_id=club_id)
        achievements = [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "reward_type": a.reward_type,
                "reward_value": str(a.reward_value),
                "unlocked": a.id in unlocked_ids,
            }
            for a in ach_qs.order_by("name")
        ]

        return Response({
            "deposit_money": str(deposit),
            "bonus_balance": str(bonus),
            "achievements": achievements,
            "unlocked_count": len([a for a in achievements if a["unlocked"]]),
            "total_count": len(achievements),
        })


class ApplyPromocodeAPIView(APIView):
    """POST /api/v1/loyalty/promocodes/apply/

    Body: { code: str, client_id: int, channel?: 'admin'|'mobile'|'shell' }
    Returns: { ok, reward_type, value, message }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.db import IntegrityError, transaction
        from django.db.models import F
        from apps.clubs.api.v1.mixins import validated_club_id

        code = (request.data.get('code') or '').strip()
        client_id = request.data.get('client_id')
        channel = request.data.get('channel') or 'admin'
        if not code or not client_id:
            return Response({'ok': False, 'message': 'code и client_id обязательны'}, status=400)

        # SECURITY: scope to the authorized club so club A can't burn club B's promo.
        cid = validated_club_id(request)
        if not cid:
            return Response({'ok': False, 'message': 'Нет доступа к клубу'}, status=403)

        try:
            p = Promocode.objects.get(code=code, is_active=True, club_id=cid)
        except Promocode.DoesNotExist:
            return Response({'ok': False, 'message': 'Промокод не найден или отключён'}, status=404)

        now = timezone.now()
        if p.valid_from and p.valid_from > now:
            return Response({'ok': False, 'message': 'Промокод ещё не активен'}, status=400)
        if p.valid_until and p.valid_until < now:
            return Response({'ok': False, 'message': 'Срок действия истёк'}, status=400)
        if p.channels and channel not in p.channels:
            return Response({'ok': False, 'message': f'Канал «{channel}» недоступен'}, status=400)

        # Atomically claim a use: lock the promo row, re-check the limit under the
        # lock, and let the DB unique_together(promocode,client) enforce once-per-client.
        # Was a check-then-act race that could blow past usage_limit / double-apply.
        # H3: claim the usage AND apply the reward in ONE transaction — the reward
        # used to run AFTER the atomic block, so any failure left the code "spent"
        # (usage recorded) with nothing credited and the view still returned ok=True.
        message = ''
        try:
            with transaction.atomic():
                locked = Promocode.objects.select_for_update().get(pk=p.pk)
                if locked.is_exhausted:
                    return Response({'ok': False, 'message': 'Лимит использований исчерпан'}, status=400)
                try:
                    PromocodeUsage.objects.create(promocode=locked, client_id=client_id)
                except IntegrityError:
                    return Response({'ok': False, 'message': 'Этот промокод уже использован клиентом'}, status=400)
                Promocode.objects.filter(pk=locked.pk).update(usage_count=F('usage_count') + 1)

                if p.reward_type == PromocodeRewardType.DISCOUNT:
                    message = f'Скидка {p.value}% применена'
                elif cid:
                    from apps.clubs.models import UserClubProfile
                    profile, _ = UserClubProfile.objects.select_for_update().get_or_create(
                        user_id=client_id, club_id=cid,
                    )
                    if p.reward_type == PromocodeRewardType.DEPOSIT_TOPUP:
                        profile.deposit_money = (profile.deposit_money or Decimal('0')) + Decimal(str(p.value))
                        profile.save(update_fields=['deposit_money'])
                        message = f'Депозит пополнен на {p.value} сум'
                    elif p.reward_type == PromocodeRewardType.BONUS_TOPUP:
                        profile.bonus_balance = (profile.bonus_balance or Decimal('0')) + Decimal(str(p.value))
                        profile.save(update_fields=['bonus_balance'])
                        message = f'Бонусы пополнены на {p.value} сум'
        except IntegrityError:
            return Response({'ok': False, 'message': 'Этот промокод уже использован клиентом'}, status=400)
        except Exception as e:
            # Reward failed → whole transaction rolled back (usage NOT claimed).
            return Response({'ok': False, 'message': f'Ошибка применения промокода: {e}'}, status=400)

        return Response({
            'ok': True,
            'reward_type': p.reward_type,
            'value': str(p.value),
            'message': message,
        })


class TopupDepositAPIView(APIView):
    """POST /api/v1/clubs/topup/

    Body: { client_id: int, amount: float, method: 'cash'|'card'|... , note?: str }
    Returns: { ok, new_deposit, cashback_added, payment_id }
    Computes cashback via CashbackRule and credits bonus_balance.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.db import transaction
        from apps.clubs.models import UserClubProfile
        from apps.clubs.api.v1.mixins import validated_club_id
        from apps.billing.models import Payment, PaymentMethod

        client_id = request.data.get('client_id')
        try:
            amount = Decimal(str(request.data.get('amount') or 0))
        except Exception:
            return Response({'ok': False, 'message': 'Некорректная сумма'}, status=400)
        method = request.data.get('method', 'cash')
        note = request.data.get('note', '')
        # SECURITY: was trusting X-Club-Id/query/body → could credit deposit into ANY club.
        club_id = validated_club_id(request)

        if not client_id or not club_id or amount <= 0:
            return Response({'ok': False, 'message': 'client_id, club и amount > 0 обязательны'}, status=400)

        from apps.clubs.models import ClubSettings
        bonus_on = ClubSettings.get_bool(club_id, 'bonus_system', True)
        cashback = Decimal('0')

        # Atomic read-modify-write — concurrent topups would otherwise lose updates.
        with transaction.atomic():
            profile, _ = UserClubProfile.objects.select_for_update().get_or_create(
                user_id=client_id, club_id=club_id,
            )
            profile.deposit_money = (profile.deposit_money or Decimal('0')) + amount

            # Compute cashback (highest matching threshold) — only when the club's
            # «Бонусная система» setting is enabled.
            if bonus_on:
                from django.db.models import Q as _Q
                from django.utils import timezone as _tz
                rule = CashbackRule.objects.filter(
                    club_id=club_id, is_active=True, deposit_threshold__lte=amount,
                ).filter(_Q(valid_until__isnull=True) | _Q(valid_until__gte=_tz.now())
                ).order_by('-deposit_threshold').first()
                if rule:
                    cashback = rule.compute_reward(amount)
                    profile.bonus_balance = (profile.bonus_balance or Decimal('0')) + cashback

            profile.save(update_fields=['deposit_money', 'bonus_balance'])

        # Record Payment
        try:
            method_map = {
                'cash': PaymentMethod.CASH, 'card': PaymentMethod.CARD,
                'transfer': PaymentMethod.TRANSFER,
            }
            p = Payment.objects.create(
                user_id=client_id,
                admin=request.user if request.user.is_authenticated else None,
                amount_paid=amount,
                minutes_added=0,
                payment_method=method_map.get(method, PaymentMethod.CASH),
                # BUGFIX: was created without club_id → invisible to the per-club shift
                # Z-report/analytics and broke refund club resolution. Stamp the club.
                club_id=club_id,
                note="[TOPUP]",
            )
            payment_id = p.id
        except Exception:
            payment_id = None

        return Response({
            'ok': True,
            'new_deposit': str(profile.deposit_money),
            'cashback_added': str(cashback),
            'payment_id': payment_id,
            'note': note,
        })
