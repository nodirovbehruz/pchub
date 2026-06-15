"""Platform admin (SaaS operator) endpoints — manage ALL clubs, subscriptions, plans, users.

Access restricted to user_type='admin' (platform-level), NOT club owners.
Mounted at /api/v1/platform/.
"""
from decimal import Decimal

from django.db.models import Count, Sum, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class IsPlatformAdmin(permissions.BasePermission):
    """Only platform-level admins (user_type='admin')."""
    message = "Доступ только для платформенных администраторов."

    def has_permission(self, request, view):
        u = request.user
        return bool(
            u and u.is_authenticated and u.is_active
            and getattr(u, "user_type", "") == "admin"
        )


def _d(v):
    return float(v or 0)


# ════════════════════════════════════════════════════════════════════════
#  DASHBOARD
# ════════════════════════════════════════════════════════════════════════
class PlatformDashboardAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from apps.clubs.models import Club, ClubSubscription, PromisedPayment, SubscriptionStatus
        from apps.billing.models import Payment

        now = timezone.now()
        clubs = Club.objects.all()
        total_clubs = clubs.count()
        active_clubs = clubs.filter(is_active=True).count()

        subs = ClubSubscription.objects.select_related("plan", "club")
        by_status = {s: 0 for s in [
            SubscriptionStatus.TRIAL, SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PROMISED, SubscriptionStatus.EXPIRED, SubscriptionStatus.BLOCKED]}
        mrr = Decimal("0")
        for s in subs:
            by_status[s.status] = by_status.get(s.status, 0) + 1
            if s.status == SubscriptionStatus.ACTIVE and s.plan:
                mrr += s.plan.monthly_price

        # Trials expiring within 7 days
        soon = now + timezone.timedelta(days=7)
        expiring = clubs.filter(
            is_trial=True, trial_until__gte=now, trial_until__lte=soon
        ).count()

        # Overdue promised payments
        overdue_debts = PromisedPayment.objects.filter(
            paid_at__isnull=True, due_at__lt=now
        ).count()

        # New clubs this month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_this_month = clubs.filter(created_at__gte=month_start).count()

        # Платформенная выручка с подписок — приблизительно сумма активных планов
        # (реальный биллинг подписок ведётся отдельно; здесь — потенциальный MRR)
        return Response({
            "total_clubs": total_clubs,
            "active_clubs": active_clubs,
            "trials": by_status.get(SubscriptionStatus.TRIAL, 0),
            "active_subs": by_status.get(SubscriptionStatus.ACTIVE, 0),
            "promised": by_status.get(SubscriptionStatus.PROMISED, 0),
            "expired": by_status.get(SubscriptionStatus.EXPIRED, 0),
            "blocked": by_status.get(SubscriptionStatus.BLOCKED, 0),
            "mrr": _d(mrr),
            "expiring_trials": expiring,
            "overdue_debts": overdue_debts,
            "new_clubs_this_month": new_this_month,
        })


# ════════════════════════════════════════════════════════════════════════
#  CLUBS
# ════════════════════════════════════════════════════════════════════════
class PlatformClubsAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from apps.clubs.models import Club, SubscriptionStatus
        from apps.computers.models import Computer
        from apps.billing.models import Payment

        search = (request.query_params.get("search") or "").strip()
        status_filter = request.query_params.get("status")

        clubs = Club.objects.select_related("owner").order_by("-created_at")
        if search:
            clubs = clubs.filter(Q(name__icontains=search) | Q(owner__username__icontains=search))

        # Precompute PC counts + revenue maps (avoid N+1)
        pc_counts = {
            r["club_id"]: r["n"] for r in
            Computer.objects.filter(is_active=True).values("club_id").annotate(n=Count("id"))
        }
        rev_map = {
            r["club_id"]: _d(r["s"]) for r in
            Payment.objects.exclude(note__icontains="[REFUNDED]")
            .values("club_id").annotate(s=Sum("amount_paid"))
        }

        now = timezone.now()
        rows = []
        for c in clubs:
            try:
                sub = c.subscription
                sstatus = sub.status
                plan = sub.plan.name if sub.plan else "Free"
                expires = sub.expires_at
            except Exception:
                sstatus = SubscriptionStatus.TRIAL if c.is_trial else SubscriptionStatus.ACTIVE
                plan = "Free"
                expires = c.trial_until
            if sstatus == SubscriptionStatus.TRIAL and c.trial_until and now > c.trial_until:
                sstatus = SubscriptionStatus.EXPIRED

            if status_filter and sstatus != status_filter:
                continue

            rows.append({
                "id": c.id,
                "name": c.name,
                "city": c.city or "",
                "owner": c.owner.username if c.owner else "—",
                "owner_phone": str(getattr(c.owner, "phone", "") or "") if c.owner else "",
                "status": sstatus,
                "plan": plan,
                "is_trial": c.is_trial,
                "trial_until": c.trial_until.isoformat() if c.trial_until else None,
                "expires_at": expires.isoformat() if expires else None,
                "pc_count": pc_counts.get(c.id, 0),
                "revenue": rev_map.get(c.id, 0),
                "created_at": c.created_at.isoformat(),
                "club_token": c.club_token,
            })
        return Response({"results": rows, "count": len(rows)})


class PlatformClubDetailAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request, pk):
        from apps.clubs.models import Club, PromisedPayment, SubscriptionStatus
        from apps.computers.models import Computer
        from apps.clubs.models import UserClubProfile
        from apps.billing.models import Payment

        try:
            c = Club.objects.select_related("owner").get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        try:
            sub = c.subscription
            sstatus, plan, expires = sub.status, (sub.plan.name if sub.plan else "Free"), sub.expires_at
        except Exception:
            sub = None
            sstatus = SubscriptionStatus.TRIAL if c.is_trial else SubscriptionStatus.ACTIVE
            plan, expires = "Free", c.trial_until

        promised = []
        if sub:
            for pp in PromisedPayment.objects.filter(subscription=sub).order_by("-granted_at"):
                promised.append({
                    "id": pp.id, "fee": str(pp.fee_amount),
                    "granted_at": pp.granted_at.isoformat(),
                    "due_at": pp.due_at.isoformat(),
                    "paid": pp.paid_at is not None,
                    "overdue": pp.paid_at is None and now > pp.due_at,
                })

        revenue = _d(Payment.objects.filter(club_id=c.id).exclude(note__icontains="[REFUNDED]")
                     .aggregate(s=Sum("amount_paid"))["s"])

        return Response({
            "id": c.id, "name": c.name, "city": c.city or "", "country": c.country or "",
            "address": c.address, "site": c.site or "", "contact_phone": c.contact_phone or "",
            "owner": {
                "id": c.owner_id,
                "username": c.owner.username if c.owner else "—",
                "phone": str(getattr(c.owner, "phone", "") or "") if c.owner else "",
                "email": c.owner.email if c.owner else "",
            } if c.owner else None,
            "status": sstatus, "plan": plan, "is_trial": c.is_trial,
            "trial_until": c.trial_until.isoformat() if c.trial_until else None,
            "expires_at": expires.isoformat() if expires else None,
            "club_token": c.club_token,
            "created_at": c.created_at.isoformat(),
            "pc_count": Computer.objects.filter(club_id=c.id, is_active=True).count(),
            "client_count": UserClubProfile.objects.filter(club_id=c.id).count(),
            "revenue": revenue,
            "promised_payments": promised,
        })


class PlatformClubManageAPIView(APIView):
    """POST actions: extend_trial / activate / block / unblock."""
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        from apps.clubs.models import Club, ClubSubscription, SubscriptionPlan, SubscriptionStatus

        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)

        def _safe_days(raw, default):
            try:
                return max(1, min(3650, int(raw)))
            except (TypeError, ValueError):
                return default

        action = request.data.get("action")
        free, _ = SubscriptionPlan.objects.get_or_create(
            tier="free", defaults={"name": "Free", "monthly_price": 0, "max_pcs": 0})
        sub, _ = ClubSubscription.objects.get_or_create(club=club, defaults={"plan": free})
        now = timezone.now()

        if action == "extend_trial":
            days = _safe_days(request.data.get("days", 14), 14)
            club.trial_until = now + timezone.timedelta(days=days)
            club.is_trial = True
            club.save(update_fields=["trial_until", "is_trial"])
            sub.status = SubscriptionStatus.TRIAL
            sub.expires_at = club.trial_until
            sub.save(update_fields=["status", "expires_at"])
        elif action == "activate":
            tier = request.data.get("tier", "starter")
            days = _safe_days(request.data.get("days", 30), 30)
            plan = SubscriptionPlan.objects.filter(tier=tier).first()
            if not plan:
                return Response({"error": f"Тариф «{tier}» не найден"}, status=status.HTTP_400_BAD_REQUEST)
            sub.plan = plan
            sub.status = SubscriptionStatus.ACTIVE
            sub.expires_at = now + timezone.timedelta(days=days)
            sub.save(update_fields=["plan", "status", "expires_at"])
            club.is_trial = False
            club.save(update_fields=["is_trial"])
        elif action == "block":
            sub.status = SubscriptionStatus.BLOCKED
            sub.save(update_fields=["status"])
        elif action == "unblock":
            sub.status = SubscriptionStatus.ACTIVE
            # H7: also push expires_at into the future — otherwise subscription_active()
            # still sees a past expiry and the club re-blocks on the next request
            # (unblock was a visual no-op). Grant a 30-day period from now.
            fields = ["status"]
            if not sub.expires_at or sub.expires_at <= now:
                sub.expires_at = now + timezone.timedelta(days=30)
                fields.append("expires_at")
            sub.save(update_fields=fields)
        else:
            return Response({"error": "action: extend_trial|activate|block|unblock"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "status": sub.status})


# ════════════════════════════════════════════════════════════════════════
#  SUBSCRIPTION PLANS (тарифы платформы)
# ════════════════════════════════════════════════════════════════════════
class PlatformPlansAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from apps.clubs.models import SubscriptionPlan, ClubSubscription
        plans = SubscriptionPlan.objects.all().order_by("monthly_price")
        out = []
        for p in plans:
            out.append({
                "id": p.id, "tier": p.tier, "name": p.name,
                "monthly_price": _d(p.monthly_price), "max_pcs": p.max_pcs,
                "features": p.features, "is_active": p.is_active,
                "clubs_count": ClubSubscription.objects.filter(plan=p).count(),
            })
        return Response(out)

    def post(self, request):
        from apps.clubs.models import SubscriptionPlan
        tier = (request.data.get("tier") or "").strip()
        name = (request.data.get("name") or "").strip()
        if not tier or not name:
            return Response({"error": "tier и name обязательны"}, status=status.HTTP_400_BAD_REQUEST)
        if SubscriptionPlan.objects.filter(tier=tier).exists():
            return Response({"error": "Тариф с таким tier уже есть"}, status=status.HTTP_400_BAD_REQUEST)
        p = SubscriptionPlan.objects.create(
            tier=tier, name=name,
            monthly_price=Decimal(str(request.data.get("monthly_price", 0) or 0)),
            max_pcs=int(request.data.get("max_pcs", 0) or 0),
            features=request.data.get("features", {}) or {},
        )
        return Response({"id": p.id, "tier": p.tier, "name": p.name}, status=status.HTTP_201_CREATED)


class PlatformPlanDetailAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def patch(self, request, pk):
        from apps.clubs.models import SubscriptionPlan
        try:
            p = SubscriptionPlan.objects.get(pk=pk)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            if "name" in request.data: p.name = str(request.data["name"])[:120]
            if "monthly_price" in request.data: p.monthly_price = Decimal(str(request.data["monthly_price"]))
            if "max_pcs" in request.data: p.max_pcs = max(0, int(request.data["max_pcs"]))
            if "features" in request.data and isinstance(request.data["features"], dict):
                p.features = request.data["features"]
            if "is_active" in request.data: p.is_active = bool(request.data["is_active"])
        except (ValueError, TypeError, ArithmeticError):
            return Response({"error": "Некорректные данные тарифа"}, status=status.HTTP_400_BAD_REQUEST)
        p.save()
        return Response({"success": True})

    def delete(self, request, pk):
        from apps.clubs.models import SubscriptionPlan, ClubSubscription
        try:
            p = SubscriptionPlan.objects.get(pk=pk)
        except SubscriptionPlan.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        if ClubSubscription.objects.filter(plan=p).exists():
            return Response(
                {"error": "Нельзя удалить тариф — на нём есть клубы. Сначала переведите их на другой тариф."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        p.delete()
        return Response({"success": True})


# ════════════════════════════════════════════════════════════════════════
#  USERS / OWNERS / EMPLOYEES
# ════════════════════════════════════════════════════════════════════════
class PlatformUsersAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from apps.accounts.models import CustomUser
        kind = request.query_params.get("kind", "all")  # all|client|staff|owner|admin
        search = (request.query_params.get("search") or "").strip()

        qs = CustomUser.objects.all().order_by("-created_at")
        if kind == "client":
            qs = qs.filter(user_type="user")
        elif kind == "owner":
            qs = qs.filter(user_type="owner")
        elif kind == "admin":
            qs = qs.filter(user_type="admin")
        elif kind == "staff":
            qs = qs.filter(user_type__in=["manager", "operator", "admin", "owner"])
        if search:
            qs = qs.filter(Q(username__icontains=search) | Q(phone__icontains=search)
                           | Q(first_name__icontains=search) | Q(last_name__icontains=search))

        rows = [{
            "id": u.id, "username": u.username,
            "full_name": f"{u.first_name} {u.last_name}".strip(),
            "phone": str(getattr(u, "phone", "") or ""),
            "email": u.email or "", "user_type": u.user_type,
            "is_active": u.is_active,
            "joined": u.created_at.isoformat() if getattr(u, "created_at", None) else None,
        } for u in qs[:300]]
        return Response({"results": rows, "count": len(rows)})


class PlatformEmployeesAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        from apps.clubs.models import ClubMembership
        rows = []
        for m in (ClubMembership.objects.filter(is_active=True)
                  .select_related("user", "club").order_by("club__name")):
            rows.append({
                "user_id": m.user_id,
                "username": m.user.username if m.user else "—",
                "club": m.club.name if m.club else "—",
                "club_id": m.club_id,
                "role": m.role,
            })
        return Response({"results": rows, "count": len(rows)})


# ════════════════════════════════════════════════════════════════════════
#  CREATE CLUB + OWNER (онбординг)
# ════════════════════════════════════════════════════════════════════════
class PlatformClubCreateAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        from django.utils import timezone
        from apps.accounts.models import CustomUser, USER_TYPES
        from apps.clubs.models import Club, ClubMembership, ClubSettings

        name = (request.data.get("name") or "").strip()
        city = (request.data.get("city") or "").strip()
        owner_username = (request.data.get("owner_username") or "").strip()
        owner_password = (request.data.get("owner_password") or "").strip()
        owner_phone = (request.data.get("owner_phone") or "").strip()
        trial_days = int(request.data.get("trial_days", 14) or 14)

        from django.db import transaction, IntegrityError
        from apps.clubs.models import ClubSubscription, SubscriptionPlan, SubscriptionStatus

        if not name:
            return Response({"error": "Название клуба обязательно"}, status=status.HTTP_400_BAD_REQUEST)
        if not owner_username:
            return Response({"error": "Логин владельца обязателен"}, status=status.HTTP_400_BAD_REQUEST)
        if not owner_password or len(owner_password) < 6:
            return Response({"error": "Пароль владельца — минимум 6 символов"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            trial_days = max(1, min(3650, int(trial_days)))
        except (TypeError, ValueError):
            trial_days = 14

        # Block silently hijacking an existing CLIENT account.
        existing = CustomUser.objects.filter(username__iexact=owner_username).first()
        if existing and existing.user_type == USER_TYPES.USER:
            return Response(
                {"error": f"Логин «{owner_username}» уже занят клиентом. Выберите другой."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trial_until = timezone.now() + timezone.timedelta(days=trial_days)
        try:
            with transaction.atomic():
                # Owner: reuse only existing owner/admin, else create fresh
                if existing:
                    owner = existing  # already owner/admin/manager/operator — link as owner
                    if owner.user_type not in (USER_TYPES.OWNER, USER_TYPES.ADMIN):
                        owner.user_type = USER_TYPES.OWNER
                        owner.is_staff = True
                        owner.save(update_fields=["user_type", "is_staff"])
                else:
                    owner = CustomUser(username=owner_username, user_type=USER_TYPES.OWNER, is_staff=True)
                    if owner_phone:
                        try: owner.phone = owner_phone
                        except Exception: pass
                    owner.set_password(owner_password)
                    owner.save()

                club = Club.objects.create(name=name, city=city, owner=owner, is_trial=True, trial_until=trial_until)
                ClubSettings.objects.get_or_create(club=club)
                ClubMembership.objects.get_or_create(
                    user=owner, club=club, defaults={"role": "owner", "is_active": True})
                free, _ = SubscriptionPlan.objects.get_or_create(
                    tier="free", defaults={"name": "Free", "monthly_price": 0, "max_pcs": 0})
                ClubSubscription.objects.get_or_create(
                    club=club, defaults={"plan": free, "status": SubscriptionStatus.TRIAL, "expires_at": trial_until})
        except IntegrityError as e:
            return Response({"error": f"Конфликт данных (логин/телефон уже заняты): {e}"},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "id": club.id, "name": club.name, "token": club.club_token,
            "owner": owner.username, "trial_until": trial_until.isoformat(),
        }, status=status.HTTP_201_CREATED)


# ════════════════════════════════════════════════════════════════════════
#  USER ACTIONS (block / reset password / platform admin)
# ════════════════════════════════════════════════════════════════════════
class PlatformUserActionAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        from apps.accounts.models import CustomUser, USER_TYPES
        try:
            u = CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")
        if u.id == request.user.id and action in ("block", "unset_admin"):
            return Response({"error": "Нельзя применить это действие к себе"}, status=status.HTTP_400_BAD_REQUEST)

        if action == "block":
            u.is_active = False
            u.is_active_session = False
            u.save(update_fields=["is_active", "is_active_session"])
        elif action == "unblock":
            u.is_active = True
            u.save(update_fields=["is_active"])
        elif action == "reset_password":
            new_pw = (request.data.get("password") or "").strip()
            if len(new_pw) < 6:
                return Response({"error": "Пароль — минимум 6 символов"}, status=status.HTTP_400_BAD_REQUEST)
            u.set_password(new_pw)
            u.save()
        elif action == "set_admin":
            u.user_type = USER_TYPES.ADMIN
            u.is_staff = True
            u.save(update_fields=["user_type", "is_staff"])
        elif action == "unset_admin":
            u.user_type = USER_TYPES.USER
            u.is_staff = False
            u.save(update_fields=["user_type", "is_staff"])
        else:
            return Response({"error": "action: block|unblock|reset_password|set_admin|unset_admin"},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "is_active": u.is_active, "user_type": u.user_type})


# ════════════════════════════════════════════════════════════════════════
#  IMPERSONATE (войти как клуб) — audited
# ════════════════════════════════════════════════════════════════════════
class PlatformImpersonateAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, pk):
        from apps.clubs.models import Club
        try:
            club = Club.objects.get(pk=pk)
        except Club.DoesNotExist:
            return Response({"error": "Club not found"}, status=status.HTTP_404_NOT_FOUND)
        # Audit
        try:
            from apps.billing.models import OperationLog, LogAction
            OperationLog.objects.create(
                club_id=club.id, subject=request.user,
                object_type="Club", object_id=str(club.id),
                object_repr=f"Платформа: вход как клуб «{club.name}»",
                action=LogAction.AUTH_LOGIN,
                payload={"impersonate": True, "admin": request.user.username},
            )
        except Exception:
            pass
        return Response({"club_id": club.id, "club_name": club.name})


# ════════════════════════════════════════════════════════════════════════
#  SUBSCRIPTION BILLING — record payment / history
# ════════════════════════════════════════════════════════════════════════
class PlatformBillingAPIView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        """Platform revenue from subscription payments (PromisedPayment marked paid)."""
        from apps.clubs.models import PromisedPayment
        paid = (PromisedPayment.objects.filter(paid_at__isnull=False)
                .select_related("subscription", "subscription__club").order_by("-paid_at"))
        rows = [{
            "id": p.id,
            "club": p.subscription.club.name if p.subscription and p.subscription.club else "—",
            "amount": str(p.fee_amount),
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        } for p in paid[:100]]
        total = sum(_d(p.fee_amount) for p in paid)
        return Response({"results": rows, "total_collected": total, "count": len(rows)})
