"""Analytics endpoint — SmartShell-style aggregated metrics over a date range.

GET /api/v1/billing/analytics/?club=<id>&from=YYYY-MM-DD&to=YYYY-MM-DD
"""
from decimal import Decimal
from datetime import datetime, timedelta

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView


def _d(v):
    return float(v or 0)


def _parse_range(request):
    """Returns (club_id, date_from, date_to) or raises ValueError."""
    now = timezone.now()
    # SECURITY: validate membership against the authenticated user — a raw ?club=
    # fallback let any logged-in user read another club's analytics.
    from apps.clubs.api.v1.mixins import validated_club_id
    club_id = validated_club_id(request)
    if not club_id:
        raise ValueError("club required")

    to_str = request.query_params.get("to")
    from_str = request.query_params.get("from")
    try:
        date_to = datetime.strptime(to_str, "%Y-%m-%d").date() if to_str else now.date()
    except ValueError:
        date_to = now.date()
    try:
        date_from = datetime.strptime(from_str, "%Y-%m-%d").date() if from_str else (date_to - timedelta(days=30))
    except ValueError:
        date_from = date_to - timedelta(days=30)
    return club_id, date_from, date_to


class AnalyticsOverviewAPIView(APIView):
    """Aggregated analytics for the Обзорный (overview) tab."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.billing.models import Payment, CashOrder, CashOrderType
        from apps.computers.models import Computer

        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)
        if not club_id:
            return Response({"error": "club required or no access"}, status=403)

        # ── Date range ──
        now = timezone.now()
        to_str = request.query_params.get("to")
        from_str = request.query_params.get("from")
        try:
            date_to = datetime.strptime(to_str, "%Y-%m-%d").date() if to_str else now.date()
        except ValueError:
            date_to = now.date()
        try:
            date_from = datetime.strptime(from_str, "%Y-%m-%d").date() if from_str else (date_to - timedelta(days=30))
        except ValueError:
            date_from = date_to - timedelta(days=30)

        # ── Payments in range (exclude refunded) ──
        payments = Payment.objects.filter(
            club_id=club_id,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        ).exclude(note__icontains="[REFUNDED]")

        total_revenue = payments.aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")

        # ── Revenue by payment method ──
        def method_sum(m):
            return payments.filter(payment_method=m).aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")
        cash_rev = method_sum("cash")
        card_rev = method_sum("card")
        online_rev = (
            payments.filter(payment_method__in=["transfer", "sbp", "online"])
            .aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")
        )
        deposit_pay = method_sum("deposit")

        # ── Income per PC ──
        pc_count = Computer.objects.filter(club_id=club_id, is_active=True).count()
        income_per_pc = (total_revenue / pc_count) if pc_count else Decimal("0")

        # ── Cash orders (ПКО / РКО) ──
        cash_orders = CashOrder.objects.filter(
            club_id=club_id,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        pko_total = cash_orders.filter(type=CashOrderType.INCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        rko_total = cash_orders.filter(type=CashOrderType.OUTCOME).aggregate(s=Sum("amount"))["s"] or Decimal("0")

        # ── Deposit topups (money clients put on deposit) ──
        # Topup = not a POS sale, not postpaid, no minutes added (pure deposit credit)
        deposit_topups = (
            payments.filter(minutes_added=0)
            .exclude(note__contains="[POS]")
            .exclude(note__contains="[POSTPAID]")
            .aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")
        )
        deposit_pct = (float(deposit_topups) / float(total_revenue) * 100) if total_revenue else 0

        # ── Client spending distribution: tariffs / products / services ──
        tariffs_rev = (
            payments.filter(minutes_added__gt=0)
            .aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")
        )
        pos_rev = (
            payments.filter(note__contains="[POS]")
            .aggregate(s=Sum("amount_paid"))["s"] or Decimal("0")
        )
        # We don't split products vs services in Payment; report POS as products, services 0
        spend_total = float(tariffs_rev) + float(pos_rev)
        spend = {
            "tariffs":  float(tariffs_rev),
            "products": float(pos_rev),
            "services": 0.0,
            "total":    spend_total,
        }

        # ── Clients: unique / new / returning / guests / ARPU ──
        client_payments = payments.filter(user__isnull=False)
        client_ids = set(client_payments.values_list("user_id", flat=True))
        unique_clients = len(client_ids)

        prior_ids = set(
            Payment.objects.filter(club_id=club_id, created_at__date__lt=date_from, user__isnull=False)
            .values_list("user_id", flat=True)
        )
        new_clients = len(client_ids - prior_ids)
        returning_clients = len(client_ids & prior_ids)

        guest_sessions = payments.filter(user__isnull=True).count()
        arpu = (float(total_revenue) / unique_clients) if unique_clients else 0

        # ── Visit distribution (distinct visit-days per client) ──
        visit_days = (
            client_payments.annotate(d=TruncDate("created_at"))
            .values("user_id", "d").distinct()
        )
        visits_per_client = {}
        for row in visit_days:
            uid = row["user_id"]
            visits_per_client[uid] = visits_per_client.get(uid, 0) + 1
        buckets = {"1": 0, "2": 0, "3-4": 0, "5-9": 0, "10+": 0}
        for v in visits_per_client.values():
            if v == 1:   buckets["1"] += 1
            elif v == 2: buckets["2"] += 1
            elif v <= 4: buckets["3-4"] += 1
            elif v <= 9: buckets["5-9"] += 1
            else:        buckets["10+"] += 1
        total_visitors = sum(buckets.values()) or 1
        visit_distribution = [
            {"label": k, "count": v, "pct": round(v / total_visitors * 100, 1)}
            for k, v in buckets.items()
        ]

        # ── Bonuses (best-effort; we store bonus in UserClubProfile) ──
        bonus_total = Decimal("0")
        try:
            from apps.clubs.models import UserClubProfile
            bonus_total = (
                UserClubProfile.objects.filter(club_id=club_id)
                .aggregate(s=Sum("bonus_balance"))["s"] or Decimal("0")
            )
        except Exception:
            pass

        return Response({
            "range": {"from": str(date_from), "to": str(date_to)},
            "financial": {
                "revenue":        _d(total_revenue),
                "income_per_pc":  _d(income_per_pc),
                "pko":            _d(pko_total),
                "rko":            _d(rko_total),
                "deposit_topups": _d(deposit_topups),
                "deposit_pct":    round(deposit_pct, 1),
            },
            "revenue_by_method": {
                "cash":   _d(cash_rev),
                "card":   _d(card_rev),
                "online": _d(online_rev),
                "deposit": _d(deposit_pay),
                "total":  _d(total_revenue),
            },
            "spending": spend,
            "clients": {
                "unique":    unique_clients,
                "new":       new_clients,
                "new_pct":   round(new_clients / unique_clients * 100, 1) if unique_clients else 0,
                "returning": returning_clients,
                "returning_pct": round(returning_clients / unique_clients * 100, 1) if unique_clients else 0,
                "guest_sessions": guest_sessions,
                "arpu":      round(arpu, 1),
            },
            "visit_distribution": visit_distribution,
            "bonuses": {
                "total": _d(bonus_total),
            },
            "pc_count": pc_count,
            "payment_count": payments.count(),
        })


class AnalyticsVisitorsAPIView(APIView):
    """Daily visitors breakdown for the Посетители tab."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.billing.models import Payment
        from django.db.models.functions import TruncDate

        from apps.clubs.api.v1.mixins import validated_club_id
        club_id = validated_club_id(request)
        if not club_id:
            return Response({"error": "club required or no access"}, status=403)

        now = timezone.now()
        to_str = request.query_params.get("to")
        from_str = request.query_params.get("from")
        try:
            date_to = datetime.strptime(to_str, "%Y-%m-%d").date() if to_str else now.date()
        except ValueError:
            date_to = now.date()
        try:
            date_from = datetime.strptime(from_str, "%Y-%m-%d").date() if from_str else (date_to - timedelta(days=30))
        except ValueError:
            date_from = date_to - timedelta(days=30)

        payments = Payment.objects.filter(
            club_id=club_id,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        ).exclude(note__icontains="[REFUNDED]")

        # Group by day → distinct clients + sessions (payment count as proxy)
        by_day = {}
        rows = (
            payments.annotate(d=TruncDate("created_at"))
            .values("d", "user_id")
        )
        for r in rows:
            day = r["d"]
            key = str(day)
            if key not in by_day:
                by_day[key] = {"date": key, "clients": set(), "guests": 0, "sessions": 0}
            by_day[key]["sessions"] += 1
            if r["user_id"]:
                by_day[key]["clients"].add(r["user_id"])
            else:
                by_day[key]["guests"] += 1

        daily = []
        for key in sorted(by_day.keys()):
            row = by_day[key]
            clients = len(row["clients"])
            daily.append({
                "date": key,
                "clients": clients,
                "guests": row["guests"],
                "visitors": clients + row["guests"],
                "sessions": row["sessions"],
            })

        total_clients = len(set(
            payments.filter(user__isnull=False).values_list("user_id", flat=True)
        ))
        total_guests = payments.filter(user__isnull=True).count()
        total_sessions = payments.count()
        peak = max((d["visitors"] for d in daily), default=0)
        low = min((d["visitors"] for d in daily), default=0)

        return Response({
            "range": {"from": str(date_from), "to": str(date_to)},
            "summary": {
                "total_visitors": total_clients + total_guests,
                "total_clients": total_clients,
                "total_guests": total_guests,
                "total_sessions": total_sessions,
                "peak": peak,
                "low": low,
            },
            "daily": daily,
        })


def _range_payments(club_id, date_from, date_to):
    from apps.billing.models import Payment
    return Payment.objects.filter(
        club_id=club_id,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )


class AnalyticsShiftsAPIView(APIView):
    """Per-employee shift summary (Смены tab)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            club_id, date_from, date_to = _parse_range(request)
        except (ValueError, TypeError):
            return Response({"error": "invalid params"}, status=400)

        from apps.billing.models import Shift

        payments = _range_payments(club_id, date_from, date_to)
        active = payments.exclude(note__icontains="[REFUNDED]")
        refunded = payments.filter(note__icontains="[REFUNDED]")

        # Group by admin (operator)
        emp = {}
        def row(uid, uname):
            if uid not in emp:
                emp[uid] = {"user_id": uid, "employee": uname or "—", "shifts_count": 0,
                            "worked_minutes": 0, "revenue": 0.0, "products": 0.0,
                            "services": 0.0, "bonus": 0.0, "refunds": 0.0}
            return emp[uid]

        for p in active.select_related("admin"):
            uid = p.admin_id
            uname = p.admin.username if p.admin else "—"
            r = row(uid, uname)
            amt = _d(p.amount_paid)
            r["revenue"] += amt
            if "[POS]" in (p.note or ""):
                r["products"] += amt
        for p in refunded.select_related("admin"):
            r = row(p.admin_id, p.admin.username if p.admin else "—")
            r["refunds"] += _d(p.amount_paid)

        # Shift counts + worked time
        shifts = Shift.objects.filter(
            club_id=club_id, start_time__date__gte=date_from, start_time__date__lte=date_to,
        ).select_related("admin")
        for sh in shifts:
            r = row(sh.admin_id, sh.admin.username if sh.admin else "—")
            r["shifts_count"] += 1
            if sh.end_time and sh.start_time:
                r["worked_minutes"] += int((sh.end_time - sh.start_time).total_seconds() // 60)

        rows = list(emp.values())
        rows.sort(key=lambda x: x["revenue"], reverse=True)

        summary = {
            "worked_minutes": sum(r["worked_minutes"] for r in rows),
            "revenue":  sum(r["revenue"] for r in rows),
            "products": sum(r["products"] for r in rows),
            "services": sum(r["services"] for r in rows),
            "bonus":    sum(r["bonus"] for r in rows),
            "refunds":  sum(r["refunds"] for r in rows),
        }
        return Response({"range": {"from": str(date_from), "to": str(date_to)},
                         "summary": summary, "rows": rows})


class AnalyticsClientsAPIView(APIView):
    """Per-client spending report (Клиенты tab)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            club_id, date_from, date_to = _parse_range(request)
        except (ValueError, TypeError):
            return Response({"error": "invalid params"}, status=400)

        from apps.clubs.models import UserClubProfile

        search = (request.query_params.get("search") or "").strip()
        page = max(1, int(request.query_params.get("page", 1) or 1))
        page_size = 25

        profiles = UserClubProfile.objects.filter(club_id=club_id).select_related("user")
        if search:
            from django.db.models import Q
            profiles = profiles.filter(
                Q(user__username__icontains=search) | Q(user__phone__icontains=search)
                | Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search)
            )

        # Spending per client in range
        payments = _range_payments(club_id, date_from, date_to).exclude(note__icontains="[REFUNDED]")
        spend = {}
        for p in payments.filter(user__isnull=False):
            s = spend.setdefault(p.user_id, {"total": 0.0, "tariffs": 0.0, "shop": 0.0, "count": 0})
            amt = _d(p.amount_paid)
            s["total"] += amt
            s["count"] += 1
            if "[POS]" in (p.note or ""):
                s["shop"] += amt
            elif p.minutes_added and p.minutes_added > 0:
                s["tariffs"] += amt

        all_rows = []
        for prof in profiles:
            u = prof.user
            sp = spend.get(prof.user_id, {"total": 0.0, "tariffs": 0.0, "shop": 0.0, "count": 0})
            reg = getattr(u, "created_at", None) or getattr(u, "date_joined", None)
            all_rows.append({
                "user_id": prof.user_id,
                "client": f"{u.first_name} {u.last_name}".strip() or u.username,
                "username": u.username,
                "registered_at": reg.isoformat() if reg else None,
                "balance": _d(prof.deposit_money),
                "discount": prof.personal_discount,
                "spent_total": round(sp["total"], 2),
                "spent_tariffs": round(sp["tariffs"], 2),
                "spent_shop": round(sp["shop"], 2),
                "avg_check": round(sp["total"] / sp["count"], 2) if sp["count"] else 0,
            })
        # sort by spent desc
        all_rows.sort(key=lambda x: x["spent_total"], reverse=True)

        total = len(all_rows)
        pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        rows = all_rows[start:start + page_size]

        return Response({"range": {"from": str(date_from), "to": str(date_to)},
                         "rows": rows, "total": total, "page": page, "pages": pages})


class AnalyticsEquipmentAPIView(APIView):
    """Per-PC occupancy report (Занятость оборудования tab)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            club_id, date_from, date_to = _parse_range(request)
        except (ValueError, TypeError):
            return Response({"error": "invalid params"}, status=400)

        from apps.computers.models import Computer

        period_days = (date_to - date_from).days + 1
        pcs = Computer.objects.filter(club_id=club_id, is_active=True).select_related("group")

        payments = _range_payments(club_id, date_from, date_to).exclude(note__icontains="[REFUNDED]")

        per_pc = {}
        for p in payments.filter(computer__isnull=False):
            d = per_pc.setdefault(p.computer_id, {"minutes": 0, "sessions": 0, "revenue": 0.0})
            d["minutes"] += int(p.minutes_added or 0)
            d["sessions"] += 1
            d["revenue"] += _d(p.amount_paid)

        rows = []
        total_busy_min = 0
        total_sessions = 0
        total_revenue = 0.0
        for pc in pcs:
            d = per_pc.get(pc.id, {"minutes": 0, "sessions": 0, "revenue": 0.0})
            busy_h = d["minutes"] / 60
            avail_h = period_days * 24
            rows.append({
                "pc_id": pc.id,
                "pc_name": pc.name,
                "zone": pc.group.name if pc.group else "—",
                "busy_hours": round(busy_h, 2),
                "busy_pct": round(busy_h / avail_h * 100, 1) if avail_h else 0,
                "avg_session": round(busy_h / d["sessions"], 2) if d["sessions"] else 0,
                "sessions": d["sessions"],
                "revenue": round(d["revenue"], 2),
            })
            total_busy_min += d["minutes"]
            total_sessions += d["sessions"]
            total_revenue += d["revenue"]
        rows.sort(key=lambda x: x["revenue"], reverse=True)

        pc_count = pcs.count()
        total_machine_hours = pc_count * period_days * 24
        busy_hours = total_busy_min / 60
        summary = {
            "total_machine_hours": round(total_machine_hours, 1),
            "busy_hours": round(busy_hours, 2),
            "busy_pct": round(busy_hours / total_machine_hours * 100, 2) if total_machine_hours else 0,
            "sessions": total_sessions,
            "avg_session": round(busy_hours / total_sessions, 2) if total_sessions else 0,
            "revenue": round(total_revenue, 2),
        }
        return Response({"range": {"from": str(date_from), "to": str(date_to)},
                         "summary": summary, "rows": rows})


class AnalyticsSalesAPIView(APIView):
    """Sales by item/category (Продажи tab)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            club_id, date_from, date_to = _parse_range(request)
        except (ValueError, TypeError):
            return Response({"error": "invalid params"}, status=400)

        from apps.billing.models import OperationLog, LogAction

        payments = _range_payments(club_id, date_from, date_to)
        active = payments.exclude(note__icontains="[REFUNDED]")

        items = {}  # name -> {category, qty, sum, cancels}
        def item(name, category):
            return items.setdefault(name, {"name": name, "category": category, "qty": 0, "sum": 0.0, "cancels": 0})

        # Deposit topups (no POS, no minutes) → one aggregated row
        dep_count = 0
        dep_sum = 0.0
        tariff_count = 0
        tariff_sum = 0.0
        for p in active:
            note = p.note or ""
            amt = _d(p.amount_paid)
            if "[POS]" in note or "[SHOP]" in note:
                continue  # POS/shop sales are counted via OperationLog items below;
                          # counting the Payment too double-counted shop orders.
            if "[REFUNDED]" in note:
                continue  # refunded payments are not revenue
            if "[POSTPAID]" in note:
                it = item("Постоплата", "Тариф")
                it["qty"] += 1; it["sum"] += amt
                tariff_count += 1; tariff_sum += amt
            elif p.minutes_added and p.minutes_added > 0:
                # tariff — derive name from note "[CLIENT] Тариф: X" else by minutes
                tname = None
                if "Тариф:" in note:
                    tname = note.split("Тариф:", 1)[1].strip()[:40]
                if not tname:
                    h = p.minutes_added // 60
                    m = p.minutes_added % 60
                    tname = (f"{h}ч {m}м" if h and m else f"{h} ч" if h else f"{m} мин")
                it = item(tname, "Тариф")
                it["qty"] += 1; it["sum"] += amt
                tariff_count += 1; tariff_sum += amt
            else:
                it = item("Пополнение депозита", "Пополнение депозита")
                it["qty"] += 1; it["sum"] += amt
                dep_count += 1; dep_sum += amt

        # POS items from OperationLog payloads
        products_count = 0
        products_sum = 0.0
        services_count = 0
        services_sum = 0.0
        logs = OperationLog.objects.filter(
            club_id=club_id, action=LogAction.PAYMENT_CREATE,
            created_at__date__gte=date_from, created_at__date__lte=date_to,
        ).exclude(payload={})
        for log in logs:
            for it_data in (log.payload or {}).get("items", []):
                name = it_data.get("name", "Товар")
                qty = int(it_data.get("qty", 1) or 1)
                try:
                    price = float(it_data.get("price", 0))
                except Exception:
                    price = 0
                kind = it_data.get("kind", "products")
                cat = "Услуга" if kind == "services" else "Товар"
                it = item(name, cat)
                it["qty"] += qty
                it["sum"] += price * qty
                # Route services to their own bucket (was counting services/combos as
                # products in products_sold, inconsistent with the dashboard).
                if kind == "services":
                    services_count += qty
                    services_sum += price * qty
                else:
                    products_count += qty
                    products_sum += price * qty

        rows = list(items.values())
        for r in rows:
            r["avg"] = round(r["sum"] / r["qty"], 2) if r["qty"] else 0
            r["sum"] = round(r["sum"], 2)
        rows.sort(key=lambda x: x["sum"], reverse=True)

        summary = {
            "deposit_topups": round(dep_sum, 2), "deposit_count": dep_count,
            "tariffs_sold": tariff_count, "tariffs_sum": round(tariff_sum, 2),
            "products_sold": products_count, "products_sum": round(products_sum, 2),
            "services_provided": services_count, "services_sum": round(services_sum, 2),
            "bonus_topups": 0, "bonus_count": 0,
        }
        return Response({"range": {"from": str(date_from), "to": str(date_to)},
                         "summary": summary, "rows": rows})


class AnalyticsGamesAPIView(APIView):
    """Installed games / popularity across PCs (Игры и приложения tab)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            club_id, date_from, date_to = _parse_range(request)
        except (ValueError, TypeError):
            return Response({"error": "invalid params"}, status=400)

        rows = []
        try:
            from apps.computers.models import Computer
            from apps.computers.models.computer_game import ComputerGame
            pc_ids = list(Computer.objects.filter(club_id=club_id, is_active=True).values_list("id", flat=True))
            games = (
                ComputerGame.objects.filter(computer_id__in=pc_ids)
                .select_related("game")
            )
            agg = {}
            for cg in games:
                gname = getattr(cg.game, "name", None) or getattr(cg, "name", "—")
                a = agg.setdefault(gname, {"name": gname, "installs": 0})
                a["installs"] += 1
            rows = sorted(agg.values(), key=lambda x: x["installs"], reverse=True)
        except Exception:
            rows = []

        return Response({"range": {"from": str(date_from), "to": str(date_to)},
                         "rows": rows, "total_games": len(rows)})


class AnalyticsTransfersAPIView(APIView):
    """Inter-club deposit transfers (Межклубные переводы tab)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            club_id, date_from, date_to = _parse_range(request)
        except (ValueError, TypeError):
            return Response({"error": "invalid params"}, status=400)

        from apps.billing.models import OperationLog, LogAction

        logs = OperationLog.objects.filter(
            club_id=club_id, action=LogAction.DEPOSIT_TRANSFER,
            created_at__date__gte=date_from, created_at__date__lte=date_to,
        ).select_related("subject").order_by("-created_at")

        rows = [{
            "id": l.id,
            "date": l.created_at.isoformat(),
            "object": l.object_repr,
            "operator": l.subject.username if l.subject else "—",
            "payload": l.payload,
        } for l in logs[:200]]

        return Response({"range": {"from": str(date_from), "to": str(date_to)},
                         "rows": rows, "total": len(rows)})
