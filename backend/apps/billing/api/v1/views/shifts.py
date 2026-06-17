from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import Shift
from apps.clubs.api.v1.mixins import validated_club_id


def _shift_realtime(shift):
    """Calculate real-time revenue for an open shift — filtered by club."""
    from apps.billing.models import Payment
    # Filter payments by club AND shift start time.
    # Exclude refunded payments — a refund only stamps "[REFUNDED]" in note and keeps
    # the original positive amount_paid, so counting it would overstate shift revenue.
    payments = Payment.objects.filter(created_at__gte=shift.start_time).exclude(note__icontains="[REFUNDED]")
    if shift.club_id:
        payments = payments.filter(club_id=shift.club_id)
    cash_rev = payments.filter(payment_method='cash').aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    card_rev = payments.filter(payment_method='card').aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
    total_rev = cash_rev + card_rev
    initial = Decimal(str(shift.initial_cash or 0))
    return {
        'id': shift.id,
        'opened_at': shift.start_time.isoformat() if shift.start_time else None,
        'operator': shift.admin.username if shift.admin else '',
        'initial_cash': str(initial),
        'cash_revenue': str(cash_rev),
        'card_revenue': str(card_rev),
        'expected_cash': str(initial + cash_rev),
        'total_revenue': str(total_rev),
    }


class ShiftCurrentAPIView(APIView):
    """GET current active shift info — returns real-time revenue."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # SECURITY: was trusting current_club_id/query → could read ANY club's shift revenue.
        club_id = validated_club_id(request)
        if not club_id:
            return Response({'is_active': False, 'shift': None})
        qs = Shift.objects.filter(is_active=True, club_id=club_id)
        shift = qs.order_by('-start_time').first()
        if not shift:
            return Response({'is_active': False, 'shift': None})
        return Response({'is_active': True, 'shift': _shift_realtime(shift)})


class ShiftOpenAPIView(APIView):
    """POST to open a new shift. Body: {initial_cash: float}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # SECURITY: was trusting current_club_id/body → could open a shift in ANY club.
        club_id = validated_club_id(request)
        if not club_id:
            return Response({'error': 'Нет доступа к клубу'}, status=status.HTTP_403_FORBIDDEN)

        initial_cash = float(request.data.get('initial_cash', 0) or 0)
        from django.db import transaction as _txn
        from apps.clubs.models import Club as _Club
        with _txn.atomic():
            # Serialize per-club shift opens on the Club row — the check+create was a
            # TOCTOU race (no lock, no unique constraint), so two concurrent opens both
            # passed .exists() and created two active shifts. (Logic-verified; sqlite
            # serializes writes so the race can't be reproduced under load here.)
            _Club.objects.select_for_update().filter(id=club_id).first()
            if Shift.objects.filter(is_active=True, club_id=club_id).exists():
                return Response({'error': 'Смена уже открыта'}, status=status.HTTP_400_BAD_REQUEST)
            shift = Shift.objects.create(
                admin=request.user,
                club_id=club_id,
                initial_cash=initial_cash,
                start_time=timezone.now(),
            )

        # Audit log
        try:
            from apps.billing.models import OperationLog, LogAction
            OperationLog.objects.create(
                club_id=club_id, shift=shift, subject=request.user,
                object_type="Shift", object_id=str(shift.id),
                object_repr=f"Смена #{shift.id}",
                action=LogAction.SHIFT_OPEN,
                payload={"initial_cash": str(initial_cash)},
            )
        except Exception:
            pass

        try:
            from apps.clubs.services.telegram import notify_club
            notify_club(club_id, (
                f"🔓 <b>Смена открыта</b>\n"
                f"👤 Оператор: {request.user.username}\n"
                f"💵 Начальная касса: {initial_cash} сум"
            ))
        except Exception:
            pass

        return Response({
            'success': True,
            'message': 'Смена открыта',
            'shift': {
                'id': shift.id,
                'opened_at': shift.start_time.isoformat(),
                'operator': request.user.username,
                'initial_cash': str(shift.initial_cash),
                'expected_cash': str(shift.initial_cash),
                'total_revenue_cash': '0',
                'total_revenue_card': '0',
            }
        }, status=status.HTTP_201_CREATED)


class ShiftCloseAPIView(APIView):
    """POST to close the current active shift. Body: {closing_cash: float, notes: str}"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # SECURITY: was trusting current_club_id/body → could close ANY club's shift
        # (and claim orphaned shifts into an arbitrary club).
        club_id = validated_club_id(request)
        if not club_id:
            return Response({'error': 'Нет доступа к клубу'}, status=status.HTTP_403_FORBIDDEN)
        active = Shift.objects.filter(is_active=True)

        # Primary: exact club match
        shift = active.filter(club_id=club_id).order_by('-start_time').first()
        if not shift:
            # Fallback: legacy shift without club_id (created before multi-club migration)
            shift = active.filter(club_id__isnull=True).order_by('-start_time').first()
            if shift:
                # Claim this orphaned shift for the current (authorized) club
                shift.club_id = club_id

        if not shift:
            return Response({'error': 'Нет открытой смены'}, status=status.HTTP_400_BAD_REQUEST)

        closing_cash = float(request.data.get('closing_cash', 0) or 0)
        notes = request.data.get('notes', '')
        shift.notes = notes
        shift.close_shift(closing_cash)

        # Audit log
        try:
            from apps.billing.models import OperationLog, LogAction
            OperationLog.objects.create(
                club_id=shift.club_id, shift=shift, subject=request.user,
                object_type="Shift", object_id=str(shift.id),
                object_repr=f"Смена #{shift.id}",
                action=LogAction.SHIFT_CLOSE,
                payload={
                    "closing_cash": str(closing_cash),
                    "total_revenue": str(shift.total_revenue),
                    "notes": notes,
                },
            )
        except Exception:
            pass

        try:
            from apps.clubs.services.telegram import notify_club
            notify_club(shift.club_id, (
                f"🔐 <b>Смена закрыта</b>\n"
                f"👤 Оператор: {request.user.username}\n"
                f"💵 Итоговая касса: {closing_cash} сум\n"
                f"📊 Выручка: {shift.total_revenue} сум"
            ))
        except Exception:
            pass

        return Response({'success': True, 'message': 'Смена закрыта'})
