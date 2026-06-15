import graphene
from graphene_django.types import DjangoObjectType
from .models.computer import Computer
from .models.enums import ComputerStatus


class HostType(DjangoObjectType):
    """
    Maps our Computer model to SmartShell's 'Host' object spec.
    SmartShell fields: id, alias, coord_x, coord_y, in_service, online, group_id
    """
    class Meta:
        model = Computer
        fields = (
            "id", "name", "pc_number",
            "cpu_model", "ram_total_gb", "gpu_model",
            "ip_address", "mac_address",
            "status", "is_active",
            "position_x", "position_y", "map_zone",
            "last_seen", "created_at",
        )

    # SmartShell-compatible field aliases
    alias = graphene.String(description="SmartShell alias = pc_number or name")
    coord_x = graphene.Int(description="SmartShell coord_x = position_x")
    coord_y = graphene.Int(description="SmartShell coord_y = position_y")
    in_service = graphene.Boolean(description="True if PC is not offline")
    online = graphene.Boolean(description="True if PC status is online")
    group_id = graphene.String(description="SmartShell group = map_zone")
    # Active session info
    active_user = graphene.String()
    session_end_time = graphene.String()

    def resolve_alias(self, info):
        return str(self.pc_number) if self.pc_number else self.name

    def resolve_coord_x(self, info):
        return self.position_x or 0

    def resolve_coord_y(self, info):
        return self.position_y or 0

    def resolve_in_service(self, info):
        return (self.status or "").upper() not in ("OFFLINE", "MAINTENANCE", "DISABLED")

    def resolve_online(self, info):
        return (self.status or "").upper() == "ONLINE"

    def resolve_group_id(self, info):
        if self.group_id:
            return str(self.group_id)
        return self.map_zone or "main"

    def resolve_active_user(self, info):
        if (self.status or "").upper() == "ONLINE":
            # Try to find most recent payment for this PC
            from apps.billing.models import Payment
            p = Payment.objects.filter(computer=self).select_related('user').order_by('-created_at').first()
            if p and p.user:
                return p.user.username
        return None

    def resolve_session_end_time(self, info):
        return None  # Future: calculate from start_time + minutes


class TariffType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    price = graphene.Float()
    minutes = graphene.Int()
    hours_display = graphene.String()
    is_active = graphene.Boolean()


class Query(graphene.ObjectType):
    # Exact SmartShell query name
    hosts_overview = graphene.List(HostType)
    # Added computers query matching what ClubMap uses
    computers = graphene.List(HostType)
    # Tariff plans
    tariffs = graphene.List(TariffType)

    def resolve_hosts_overview(self, info, **kwargs):
        return Computer.objects.filter(is_active=True)

    def resolve_computers(self, info, **kwargs):
        return Computer.objects.filter(is_active=True)

    def resolve_tariffs(self, info, **kwargs):
        from apps.billing.models import TariffPlan
        plans = TariffPlan.objects.all().order_by('price', 'id')
        return [
            TariffType(
                id=str(t.id),
                name=t.name,
                price=float(t.price),
                minutes=t.minutes,
                hours_display=t.hours_display,
                is_active=t.is_active,
            )
            for t in plans
        ]


class StartSessionMutation(graphene.Mutation):
    class Arguments:
        pc_id = graphene.ID(required=True)
        user_id = graphene.ID()
        tariff_id = graphene.ID()
        duration_minutes = graphene.Int()
        payment_method = graphene.String(default_value='cash')
        amount_paid = graphene.Float(default_value=0.0)

    success = graphene.Boolean()
    message = graphene.String()
    computer = graphene.Field(HostType)

    @classmethod
    def mutate(cls, root, info, pc_id, user_id=None, tariff_id=None,
               duration_minutes=None, payment_method='cash', amount_paid=0.0):
        from django.utils import timezone
        admin = info.context.user

        try:
            pc = Computer.objects.get(id=pc_id)
        except Computer.DoesNotExist:
            return StartSessionMutation(success=False, message="ПК не найден", computer=None)

        # Resolve tariff and price (with per-zone + per-period lookup)
        minutes = duration_minutes or 0
        tariff = None
        resolved_price = float(amount_paid or 0)

        if tariff_id:
            try:
                from apps.billing.models import TariffPlan, PricePeriod
                tariff = TariffPlan.objects.prefetch_related("prices").get(id=tariff_id)
                minutes = tariff.minutes

                # Determine period: if pc.group has a tariff at night window, use night
                now = timezone.localtime()
                hour = now.hour
                # SmartShell default: night = 22:00–08:00
                period = PricePeriod.NIGHT if (hour >= 22 or hour < 8) else PricePeriod.DAY

                # Try per-zone + per-period match
                if pc.group_id:
                    tp = tariff.prices.filter(group_id=pc.group_id, period=period).first() \
                        or tariff.prices.filter(group_id=pc.group_id).first()
                    if tp:
                        resolved_price = float(tp.price)

                # Fallback to base price
                if resolved_price == 0:
                    resolved_price = float(tariff.price)
            except Exception:
                pass

        # Resolve user
        target_user = None
        if user_id:
            try:
                from apps.accounts.models import CustomUser
                target_user = CustomUser.objects.get(id=user_id)
            except Exception:
                pass

        # Deduct from user balance if paying from balance
        if target_user and payment_method == 'balance' and minutes > 0:
            from apps.billing.models import UserBalance
            bal, _ = UserBalance.objects.get_or_create(user=target_user)
            if bal.minutes_remaining < minutes:
                return StartSessionMutation(success=False, message="Недостаточно времени на балансе", computer=None)
            bal.deduct_minute()
            bal.is_active = True
            bal.save()

        # Record payment if cash/card/transfer
        if payment_method in ('cash', 'card', 'transfer') and admin.is_authenticated:
            from apps.billing.models import Payment, PaymentMethod
            method_map = {'cash': PaymentMethod.CASH, 'card': PaymentMethod.CARD, 'transfer': PaymentMethod.TRANSFER}
            Payment.objects.create(
                user=target_user,
                computer=pc,
                admin=admin if admin.is_authenticated else None,
                amount_paid=resolved_price,
                minutes_added=minutes,
                payment_method=method_map.get(payment_method, PaymentMethod.CASH),
            )

        # Guest session for unregistered clients
        if not target_user:
            from apps.computers.models import GuestSession
            # Close any previous active guest session on this PC
            GuestSession.objects.filter(computer=pc, is_active=True).update(
                is_active=False, end_time=timezone.now()
            )
            GuestSession.objects.create(
                computer=pc,
                rate_per_hour=resolved_price * 60 / max(minutes, 1) if minutes else 0,
                total_amount=resolved_price,
                notes=f"Tariff: {tariff.name if tariff else 'manual'}",
            )

        pc.status = ComputerStatus.ONLINE
        pc.save(update_fields=["status"])
        return StartSessionMutation(success=True, message="Сеанс успешно начат", computer=pc)


class StopSessionMutation(graphene.Mutation):
    class Arguments:
        pc_id = graphene.ID(required=True)

    success = graphene.Boolean()
    message = graphene.String()
    computer = graphene.Field(HostType)

    @classmethod
    def mutate(cls, root, info, pc_id):
        try:
            pc = Computer.objects.get(id=pc_id)
            pc.status = ComputerStatus.OFFLINE
            pc.save()
            return StopSessionMutation(success=True, message="Сеанс завершён", computer=pc)
        except Computer.DoesNotExist:
            return StopSessionMutation(success=False, message="ПК не найден", computer=None)


class CreateTariffMutation(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        minutes = graphene.Int(required=True)

    success = graphene.Boolean()
    tariff = graphene.Field(TariffType)

    @classmethod
    def mutate(cls, root, info, name, price, minutes):
        from apps.billing.models import TariffPlan
        t = TariffPlan.objects.create(name=name, price=price, minutes=minutes, is_active=True)
        return CreateTariffMutation(
            success=True, 
            tariff=TariffType(id=str(t.id), name=t.name, price=float(t.price), minutes=t.minutes, hours_display=t.hours_display, is_active=t.is_active)
        )


class UpdateTariffMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)
        name = graphene.String()
        price = graphene.Float()
        minutes = graphene.Int()
        is_active = graphene.Boolean()

    success = graphene.Boolean()
    tariff = graphene.Field(TariffType)

    @classmethod
    def mutate(cls, root, info, id, name=None, price=None, minutes=None, is_active=None):
        from apps.billing.models import TariffPlan
        try:
            t = TariffPlan.objects.get(id=id)
            if name is not None: t.name = name
            if price is not None: t.price = price
            if minutes is not None: t.minutes = minutes
            if is_active is not None: t.is_active = is_active
            t.save()
            return UpdateTariffMutation(
                success=True, 
                tariff=TariffType(id=str(t.id), name=t.name, price=float(t.price), minutes=t.minutes, hours_display=t.hours_display, is_active=t.is_active)
            )
        except TariffPlan.DoesNotExist:
            return UpdateTariffMutation(success=False, tariff=None)


class DeleteTariffMutation(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    success = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, id):
        from apps.billing.models import TariffPlan
        try:
            t = TariffPlan.objects.get(id=id)
            t.delete() # Or set is_active=False
            return DeleteTariffMutation(success=True)
        except TariffPlan.DoesNotExist:
            return DeleteTariffMutation(success=False)


class Mutation(graphene.ObjectType):
    start_session = StartSessionMutation.Field()
    stop_session = StopSessionMutation.Field()
    create_tariff = CreateTariffMutation.Field()
    update_tariff = UpdateTariffMutation.Field()
    delete_tariff = DeleteTariffMutation.Field()

