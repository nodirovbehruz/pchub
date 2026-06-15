"""Dashboard stats endpoint — aggregates 8 widgets data per current open shift."""
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


class DashboardStatsAPIView(APIView):
    """GET /api/v1/billing/dashboard/?club=<id>

    Returns the 8 dashboard widgets data per SmartShell spec:
      1. shift_info        — operator, opened_at, expected_cash, initial_cash, cash/card revenue
      2. revenue_by_category — tariffs / products / services / topups totals
      3. bonus_activity    — bonus_topups_total / deposit_spent_total
      4. hosts_state       — total / online / active_sessions / maintenance / high_access / shell_down
      5. tasks             — active[] and finished[] lists for the current club
      6. shift_items       — services_provided[] and products_sold[] per active shift
      7. top_clients       — top users by deposit
      8. account_groups    — ClubAccount groups
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.billing.models import Payment, Shift
        from apps.computers.models import Computer
        from apps.content.models import Task
        from apps.clubs.api.v1.mixins import validated_club_id

        # SECURITY: was trusting current_club_id/query → any user could read ANY club's
        # dashboard (revenue, top clients, shift cash). Membership-checked.
        club_id = validated_club_id(request)
        if not club_id:
            return Response({'error': 'club_id required'}, status=400)

        # ── 1) Active shift — calculate revenue in REAL TIME from Payment records ──
        shift = Shift.objects.filter(is_active=True, club_id=club_id).order_by('-start_time').first()
        shift_info = None
        shift_start = None

        if shift:
            shift_start = shift.start_time
            # Real-time totals — don't use stored shift.total_revenue_* (only set at close).
            # Exclude refunds ([REFUNDED] stamped, amount kept) so revenue isn't overstated.
            shift_payments = Payment.objects.filter(
                created_at__gte=shift_start, club_id=club_id,
            ).exclude(note__icontains='[REFUNDED]')
            cash_rev = (
                shift_payments.filter(payment_method='cash')
                .aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
            )
            card_rev = (
                shift_payments.filter(payment_method='card')
                .aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
            )
            total_shift_rev = cash_rev + card_rev
            initial_cash = Decimal(str(shift.initial_cash or 0))

            shift_info = {
                'id': shift.id,
                'opened_at': shift.start_time,
                'operator': getattr(shift.admin, 'username', None) if shift.admin else None,
                'initial_cash': str(initial_cash),
                # cash_revenue = cash sales during shift
                'cash_revenue': str(cash_rev),
                # card_revenue = card sales during shift
                'card_revenue': str(card_rev),
                # expected_cash = total shift revenue (shown as "Выручка" in header)
                'expected_cash': str(total_shift_rev),
            }

        # ── 2) Revenue by category (same shift window) ──
        # Exclude refunds from every category aggregate below.
        if shift_start:
            payments_qs = Payment.objects.filter(created_at__gte=shift_start, club_id=club_id)
        else:
            from datetime import timedelta
            payments_qs = Payment.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24),
                club_id=club_id,
            )
        payments_qs = payments_qs.exclude(note__icontains='[REFUNDED]')

        # Tariffs: payments where time was added (minutes > 0), not a POS sale
        tariffs_rev = (
            payments_qs.filter(minutes_added__gt=0)
            .aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
        )

        # POS product/service sales: tagged with [POS] note
        pos_rev = (
            payments_qs.filter(note__contains='[POS]')
            .aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
        )

        # Topups: minutes_added == 0, NOT a POS sale, NOT a DEPOSIT payment
        topups_rev = (
            payments_qs
            .filter(minutes_added=0)
            .exclude(note__contains='[POS]')
            .exclude(note__contains='[DEPOSIT]')
            .aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
        )

        total_revenue = (
            payments_qs.aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
        )

        revenue_by_category = {
            'tariffs':  str(tariffs_rev),
            'products': str(pos_rev),   # POS sales (products + services + combos)
            'services': '0',            # separated in shift_items below
            'topups':   str(topups_rev),
            'total':    str(total_revenue),
        }

        # ── 3) Bonus / deposit activity ──
        bonus_activity = {
            'bonus_topups_total': '0',
            'deposit_spent_total': '0',
        }
        try:
            from apps.clubs.models import UserClubProfile
            # Deposit spent = POS sales paid via balance (tagged [DEPOSIT][POS])
            deposit_qs = payments_qs.filter(note__contains='[DEPOSIT]')
            deposit_total = deposit_qs.aggregate(s=Sum('amount_paid'))['s'] or Decimal('0')
            bonus_activity['deposit_spent_total'] = str(deposit_total)
        except Exception:
            pass

        # ── 4) Hosts state ──
        pcs = Computer.objects.filter(club_id=club_id, is_active=True)
        total = pcs.count()
        online = pcs.filter(status__iexact='online').count()
        maintenance = pcs.filter(status__iexact='maintenance').count()
        # NOTE: there is no real producer of a "shell down" status (the shell only
        # posts an empty heartbeat → ONLINE, and the staleness task only sets OFFLINE),
        # so the old shell_down filter was always 0 and the dashboard tile was removed.
        high_access = pcs.filter(high_access_active=True).count()
        offline = max(0, total - online - maintenance)

        # Real active-session count (was just `online` — i.e. powered-on PCs, so an
        # idle ONLINE PC counted as an "active session"). Count PCs with an ACTIVE
        # ClientSession plus guest-postpaid PCs, mirroring the computers list view.
        active_sessions = 0
        try:
            from apps.sessions_.models import ClientSessionStatus
            from apps.sessions_.models.client_session import SessionHost
            pc_ids = list(pcs.values_list('id', flat=True))
            occupied = set(
                SessionHost.objects.filter(
                    computer_id__in=pc_ids,
                    session__status=ClientSessionStatus.ACTIVE,
                ).values_list('computer_id', flat=True)
            )
            from apps.clubs.models import UserClubProfile
            for prof in UserClubProfile.objects.filter(
                club_id=club_id, session_mode='postpaid', is_active=True,
                user__username__startswith='guest-pc-',
            ).select_related('user'):
                try:
                    occupied.add(int(prof.user.username.rsplit('-', 1)[-1]))
                except (ValueError, IndexError):
                    pass
            active_sessions = len(occupied & set(pc_ids))
        except Exception:
            active_sessions = online
        try:
            from apps.clubs.models import UserClubProfile
            client_count = UserClubProfile.objects.filter(club_id=club_id).count()
        except Exception:
            client_count = 0

        hosts_state = {
            'total': total,
            'online': online,
            'active_sessions': active_sessions,
            'maintenance': maintenance,
            'high_access': high_access,
            'offline': offline,
            'client_count': client_count,
        }

        # ── 5) Tasks ──
        tasks_active = list(
            Task.objects.filter(club_id=club_id, is_finished=False)
            .order_by('-created_at')
            .values('id', 'title', 'body', 'created_at')[:10]
        )
        tasks_finished = list(
            Task.objects.filter(club_id=club_id, is_finished=True)
            .order_by('-finished_at')
            .values('id', 'title', 'finished_at')[:10]
        )

        # ── 6) Shift items — real sold products/services from OperationLog ──
        shift_items = {
            'services_provided': [],
            'products_sold': [],
        }
        if shift_start:
            try:
                from apps.billing.models import OperationLog, LogAction
                pos_logs = (
                    OperationLog.objects
                    .filter(
                        action=LogAction.PAYMENT_CREATE,
                        created_at__gte=shift_start,
                        club_id=club_id,
                    )
                    .exclude(payload={})
                    .order_by('-created_at')[:50]
                )
                products_sold = []
                services_provided = []
                for log in pos_logs:
                    payload = log.payload or {}
                    items = payload.get('items', [])
                    for item in items:
                        kind = item.get('kind', '')
                        qty = item.get('qty', 1) or 1
                        try:
                            unit_price = Decimal(str(item.get('price', '0')))
                            total_price = unit_price * qty
                        except Exception:
                            unit_price = Decimal('0')
                            total_price = Decimal('0')
                        entry = {
                            'name':  item.get('name', ''),
                            'qty':   qty,
                            'price': str(unit_price),
                            'total': str(total_price),
                        }
                        if kind == 'services':
                            services_provided.append(entry)
                        elif kind in ('products', 'combos'):
                            products_sold.append(entry)
                shift_items = {
                    'products_sold': products_sold,
                    'services_provided': services_provided,
                }
            except Exception:
                pass

        # ── 7) Top clients ──
        top_clients = []
        try:
            from apps.clubs.models import UserClubProfile
            top_profiles = (
                UserClubProfile.objects.filter(club_id=club_id)
                .select_related('user')
                .order_by('-deposit_money', '-last_visit_at')[:8]
            )
            top_clients = [{
                'user_id': p.user.id,
                'username': p.user.username,
                'full_name': (
                    f"{p.user.first_name or ''} {p.user.last_name or ''}".strip()
                    or p.user.username
                ),
                'deposit': str(p.deposit_money),
                'bonus': str(p.bonus_balance),
                'last_visit_at': p.last_visit_at,
            } for p in top_profiles]
        except Exception:
            pass

        # ── 8) Account groups ──
        account_groups = []
        try:
            from apps.games.models import ClubAccount
            ca = ClubAccount.objects.all()[:20]
            account_groups = [{
                'id': a.id,
                'platform': getattr(a, 'platform', ''),
                'login': getattr(a, 'login', ''),
                'in_use': False,
            } for a in ca]
        except Exception:
            pass

        return Response({
            'shift_info': shift_info,
            'revenue_by_category': revenue_by_category,
            'bonus_activity': bonus_activity,
            'hosts_state': hosts_state,
            'tasks': {'active': tasks_active, 'finished': tasks_finished},
            'shift_items': shift_items,
            'top_clients': top_clients,
            'account_groups': account_groups,
        })
