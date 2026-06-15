import graphene
from django.db.models import Sum, Q
from apps.computers.models import Computer
from apps.billing.models import Payment, PaymentMethod
from apps.billing.models.shift import Shift
from django.utils import timezone

class ShiftType(graphene.ObjectType):
    id = graphene.ID()
    is_active = graphene.Boolean()
    start_time = graphene.String()
    expected_cash = graphene.Float()
    total_revenue_cash = graphene.Float()
    total_revenue_card = graphene.Float()
    admin_name = graphene.String()


class ClientType(graphene.ObjectType):
    id = graphene.ID()
    username = graphene.String()
    full_name = graphene.String()
    phone = graphene.String()
    email = graphene.String()
    minutes_balance = graphene.Int()
    balance_formatted = graphene.String()
    user_type = graphene.String()
    is_active_session = graphene.Boolean()
    created_at = graphene.String()


class DashboardStatsType(graphene.ObjectType):
    total_revenue = graphene.Int()
    cash_revenue = graphene.Int()
    card_revenue = graphene.Int()
    total_pcs = graphene.Int()
    active_pcs = graphene.Int()
    maintenance_pcs = graphene.Int()


class AnalyticDayType(graphene.ObjectType):
    day = graphene.String()
    guests = graphene.Int()
    clients = graphene.Int()


class AnalyticsStatsType(graphene.ObjectType):
    total_machine_hours = graphene.Int()
    total_active_time = graphene.Int()
    total_sessions = graphene.Int()
    avg_session_time = graphene.Int()
    total_revenue = graphene.Int()
    daily_stats = graphene.List(AnalyticDayType)


class BookingType(graphene.ObjectType):
    pc_name = graphene.String()
    start_time = graphene.String()
    end_time = graphene.String()
    user_name = graphene.String()
    type = graphene.String()


class Query(graphene.ObjectType):
    dashboard_stats = graphene.Field(DashboardStatsType)
    analytics_stats = graphene.Field(AnalyticsStatsType)
    bookings = graphene.List(BookingType)
    current_shift = graphene.Field(ShiftType)
    clients = graphene.List(ClientType, search=graphene.String())

    def resolve_clients(self, info, search=None, **kwargs):
        from apps.accounts.models import CustomUser
        from apps.billing.models import UserBalance
        users = CustomUser.objects.filter(user_type='user', is_active=True).select_related('balance').order_by('-created_at')
        if search:
            users = users.filter(
                Q(username__icontains=search) | Q(phone__icontains=search)
            )
        result = []
        for u in users:
            try:
                bal = u.balance
                mins = bal.minutes_remaining
                fmt = bal.formatted_time
            except Exception:
                mins = 0
                fmt = '00:00'
            result.append(ClientType(
                id=str(u.id),
                username=u.username,
                full_name=u.get_full_name() or '—',
                phone=str(u.phone) if u.phone else '—',
                email=u.email or '—',
                minutes_balance=mins,
                balance_formatted=fmt,
                user_type=u.user_type,
                is_active_session=u.is_active_session,
                created_at=u.created_at.strftime('%d.%m.%Y') if u.created_at else '—',
            ))
        return result

    def resolve_current_shift(self, info, **kwargs):
        active = Shift.get_active_shift()
        if not active:
            return None
        return ShiftType(
            id=active.id,
            is_active=True,
            start_time=active.start_time.isoformat(),
            expected_cash=float(active.initial_cash + active.total_revenue_cash),
            total_revenue_cash=float(active.total_revenue_cash),
            total_revenue_card=float(active.total_revenue_card),
            admin_name=active.admin.username
        )

    def resolve_dashboard_stats(self, info, **kwargs):
        pcs_total = Computer.objects.count()
        pcs_active = Computer.objects.filter(status__iexact='online').count()
        pcs_maint = Computer.objects.filter(status__iexact='maintenance').count()

        total_q = Payment.objects.aggregate(t=Sum('amount_paid'))['t'] or 0
        cash_q = Payment.objects.filter(payment_method=PaymentMethod.CASH).aggregate(c=Sum('amount_paid'))['c'] or 0
        card_q = Payment.objects.filter(payment_method=PaymentMethod.CARD).aggregate(c=Sum('amount_paid'))['c'] or 0

        return DashboardStatsType(
            total_revenue=int(total_q),
            cash_revenue=int(cash_q),
            card_revenue=int(card_q),
            total_pcs=pcs_total,
            active_pcs=pcs_active,
            maintenance_pcs=pcs_maint,
        )

    def resolve_analytics_stats(self, info, **kwargs):
        from apps.billing.models import Payment
        total_min = Payment.objects.aggregate(s=Sum('minutes_added'))['s'] or 0
        total_sessions = Payment.objects.count()
        total_rev = Payment.objects.aggregate(t=Sum('amount_paid'))['t'] or 0

        return AnalyticsStatsType(
            total_machine_hours=int(total_min / 60),
            total_active_time=int(total_min / 60),
            total_sessions=total_sessions,
            avg_session_time=int((total_min / 60) / total_sessions) if total_sessions > 0 else 0,
            total_revenue=int(total_rev),
            daily_stats=[
                AnalyticDayType(day="Сег.", guests=int(total_rev * 0.4), clients=int(total_rev * 0.6)),
            ]
        )

    def resolve_bookings(self, info, **kwargs):
        payments = Payment.objects.select_related('computer', 'user').order_by('-created_at')[:20]
        result = []
        for p in payments:
            if p.computer:
                result.append(BookingType(
                    pc_name=p.computer.name,
                    start_time=p.created_at.strftime('%H:%M'),
                    end_time='—',
                    user_name=p.user.username if p.user else 'Guest',
                    type='accent',
                ))
        return result
class OpenShiftMutation(graphene.Mutation):
    class Arguments:
        initial_cash = graphene.Float(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    shift = graphene.Field(ShiftType)

    def mutate(self, info, initial_cash):
        user = info.context.user
        if not user.is_authenticated:
            return OpenShiftMutation(success=False, message="Не авторизован", shift=None)
            
        active = Shift.get_active_shift()
        if active:
            return OpenShiftMutation(success=False, message="Смена уже открыта", shift=None)
            
        shift = Shift.objects.create(
            admin=user,
            initial_cash=initial_cash,
            start_time=timezone.now()
        )
        t = ShiftType(
            id=shift.id, is_active=True, start_time=shift.start_time.isoformat(),
            expected_cash=float(shift.initial_cash), total_revenue_cash=0.0,
            total_revenue_card=0.0, admin_name=user.username
        )
        return OpenShiftMutation(success=True, message="Смена открыта", shift=t)


class CloseShiftMutation(graphene.Mutation):
    class Arguments:
        closing_cash = graphene.Float(required=True)
        notes = graphene.String(required=False)

    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, closing_cash, notes=""):
        user = info.context.user
        if not user.is_authenticated:
            return CloseShiftMutation(success=False, message="Не авторизован")
            
        active = Shift.get_active_shift()
        if not active:
            return CloseShiftMutation(success=False, message="Смена не открыта")
            
        active.notes = notes
        active.close_shift(closing_cash)
        return CloseShiftMutation(success=True, message="Смена успешно закрыта")


class DepositBalanceMutation(graphene.Mutation):
    class Arguments:
        user_id = graphene.ID(required=True)
        minutes = graphene.Int(required=True)
        amount_paid = graphene.Float(required=True)
        payment_method = graphene.String(default_value='cash')
        note = graphene.String(default_value='')

    success = graphene.Boolean()
    message = graphene.String()
    new_balance_minutes = graphene.Int()

    def mutate(self, info, user_id, minutes, amount_paid, payment_method='cash', note=''):
        admin = info.context.user
        if not admin.is_authenticated:
            return DepositBalanceMutation(success=False, message="Не авторизован", new_balance_minutes=0)
        
        from apps.accounts.models import CustomUser
        from apps.billing.models import UserBalance
        
        try:
            target_user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return DepositBalanceMutation(success=False, message="Пользователь не найден", new_balance_minutes=0)
        
        # Add minutes to balance
        balance, _ = UserBalance.objects.get_or_create(user=target_user)
        balance.add_minutes(minutes)
        
        # Record payment
        method_map = {'cash': PaymentMethod.CASH, 'card': PaymentMethod.CARD, 'transfer': PaymentMethod.TRANSFER}
        Payment.objects.create(
            user=target_user,
            admin=admin,
            amount_paid=amount_paid,
            minutes_added=minutes,
            payment_method=method_map.get(payment_method, PaymentMethod.CASH),
            note=note,
        )
        
        return DepositBalanceMutation(success=True, message=f"Добавлено {minutes} мин.", new_balance_minutes=balance.minutes_remaining)


class Mutation(graphene.ObjectType):
    open_shift = OpenShiftMutation.Field()
    close_shift = CloseShiftMutation.Field()
    deposit_balance = DepositBalanceMutation.Field()
