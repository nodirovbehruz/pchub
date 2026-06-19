from decimal import Decimal
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone

from apps.billing.models import Payment, PaymentMethod, UserBalance

User = get_user_model()


class BillingService:

    # ── User balance helpers ──────────────────────────────────────────────────

    def get_or_create_user_balance(self, user) -> UserBalance:
        balance, _ = UserBalance.objects.get_or_create(user=user)
        return balance

    # ── Top-up ────────────────────────────────────────────────────────────────

    def topup_user(
        self,
        user_id,
        minutes: int,
        amount_paid: Decimal,
        payment_method: str,
        admin,
        note: str = "",
        club_id=None,
    ) -> Dict[str, Any]:
        """Admin tops up a user. TIME is added to the per-club profile (so it can't
        be used at another club); money credits the club deposit. Falls back to the
        legacy global balance only when no club context is available."""
        user = User.objects.get(pk=user_id)
        balance = self.get_or_create_user_balance(user)
        profile = self._get_profile(user, club_id)

        # Add minutes — per-club when we know the club, else legacy global.
        if minutes > 0:
            (profile or balance).add_minutes(minutes)

        minutes_remaining = (profile or balance).minutes_remaining
        formatted_time = (profile or balance).formatted_time
        is_active = (profile or balance).is_active

        # Credit the club deposit so client can buy tariffs in the shell.
        # Skip for penalties — a fine is club income, not client credit.
        is_penalty = "[PENALTY]" in (note or "")
        # Mark deposit-crediting topups so a later refund can reliably DEBIT the deposit
        # back. A combined time+money topup has minutes>0, so the refund can't key off
        # minutes_added==0; session-start payments also add minutes but DON'T credit the
        # deposit and get no mark → they won't be wrongly debited on refund.
        if amount_paid > 0 and not is_penalty and "[TOPUP]" not in (note or ""):
            note = (note or "") + " [TOPUP]"
        deposit_after = Decimal("0")
        if profile and amount_paid > 0 and not is_penalty:
            try:
                from django.db import transaction as _txn
                from apps.clubs.models import UserClubProfile as _UCP
                # Lock the profile row so two concurrent top-ups (operator + shell, or a
                # double-click) can't both read the same deposit and overwrite each other.
                # The deduction side is row-locked; this credit side was a plain
                # read-modify-write → a top-up could silently vanish under concurrency.
                with _txn.atomic():
                    profile = _UCP.objects.select_for_update().get(pk=profile.pk)
                    profile.deposit_money += amount_paid
                    # BUGFIX: cashback was only computed in the orphaned /loyalty/topup/
                    # endpoint that no UI ever calls, so configured CashbackRules never
                    # credited anyone. Compute it here, in the single top-up path every
                    # UI actually uses, gated by the club's «Бонусная система» setting.
                    upd = ["deposit_money"]
                    try:
                        from apps.clubs.models import ClubSettings
                        if club_id and ClubSettings.get_bool(club_id, "bonus_system", True):
                            from apps.loyalty.models import CashbackRule
                            from django.db.models import Q as _Q
                            from django.utils import timezone as _tz
                            _now = _tz.now()
                            rule = (CashbackRule.objects
                                    .filter(club_id=club_id, is_active=True,
                                            deposit_threshold__lte=amount_paid)
                                    .filter(_Q(valid_until__isnull=True) | _Q(valid_until__gte=_now))
                                    .order_by("-deposit_threshold").first())
                            if rule:
                                cb = rule.compute_reward(amount_paid)
                                if cb:
                                    profile.bonus_balance = (profile.bonus_balance or Decimal("0")) + cb
                                    upd.append("bonus_balance")
                    except Exception:
                        pass
                    profile.save(update_fields=upd)
                    deposit_after = profile.deposit_money
            except Exception:
                pass

        payment = Payment.objects.create(
            user=user,
            admin=admin,
            amount_paid=amount_paid,
            minutes_added=minutes,
            payment_method=payment_method,
            note=note,
            club_id=club_id,
        )
        # Realtime: push the new balance to the client's shell instantly (no 30s wait).
        try:
            from realtime.broadcast import push_balance
            push_balance(user.pk, {
                "minutes_remaining": minutes_remaining,
                "formatted_time": formatted_time,
                "has_access": bool(is_active and minutes_remaining > 0),
                "session_mode": (profile or balance).session_mode,
            })
        except Exception:
            pass
        # Evaluate achievements (topup_single / topup_total) — was never invoked.
        if not is_penalty and amount_paid > 0:
            try:
                from apps.loyalty.services.achievements import evaluate_achievements
                evaluate_achievements(user, club_id, "topup", amount_paid)
            except Exception:
                pass
        return {
            "payment_id": payment.id,
            "user": user.username,
            "minutes_added": minutes,
            "minutes_remaining": minutes_remaining,
            "formatted_time": formatted_time,
            "is_active": is_active,
            "deposit_money": str(deposit_after),
        }

    # ── Deduct / Access check ─────────────────────────────────────────────────

    @staticmethod
    def _get_profile(user, club_id):
        """Per-club profile holding this club's TIME (minutes/session). Returns
        None when no club context is available (callers fall back to UserBalance)."""
        if not club_id:
            return None
        try:
            from apps.clubs.models import UserClubProfile
            profile, _ = UserClubProfile.objects.get_or_create(
                user=user, club_id=club_id,
                defaults={"personal_discount": 0, "is_blocked": False},
            )
            return profile
        except Exception:
            return None

    @staticmethod
    def _is_blocked_in_club(user, club_id) -> bool:
        """True if an operator has blocked this client in the given club."""
        if not club_id:
            return False
        try:
            from apps.clubs.models import UserClubProfile
            return UserClubProfile.objects.filter(
                user=user, club_id=club_id, is_blocked=True
            ).exists()
        except Exception:
            return False

    def deduct_minute_user(self, user, club_id=None) -> Dict[str, Any]:
        """Deduct one minute. TIME is per-club: prefer UserClubProfile, fall back
        to the legacy global UserBalance only when there is no club context."""
        # A blocked client must lose access immediately regardless of balance/mode.
        if self._is_blocked_in_club(user, club_id):
            prof = self._get_profile(user, club_id)
            return {
                "has_access": False, "blocked": True,
                "session_mode": getattr(prof, "session_mode", "prepaid"),
                "minutes_remaining": getattr(prof, "minutes_remaining", 0),
                "formatted_time": getattr(prof, "formatted_time", "00:00"),
            }

        holder = self._get_profile(user, club_id) or self.get_or_create_user_balance(user)
        has_access = holder.deduct_minute()
        result: Dict[str, Any] = {
            "has_access": has_access,
            "session_mode": holder.session_mode,
            "minutes_remaining": holder.minutes_remaining,
            "formatted_time": holder.formatted_time,
        }
        if holder.session_mode == holder.SESSION_POSTPAID:
            elapsed = self._postpaid_elapsed_minutes(holder)
            result["postpaid_minutes"] = elapsed
            # Setting: «Макс. продолжительность сеанса» — auto-revoke access when a
            # postpaid session runs past the configured cap (0 = unlimited).
            try:
                from apps.clubs.models import ClubSettings
                cap = ClubSettings.get_int(club_id, "max_session_duration", 0)
                if cap and elapsed >= cap:
                    result["has_access"] = False
                    result["session_capped"] = True
            except Exception:
                pass
        try:
            from realtime.broadcast import push_balance
            push_balance(user.pk, result)
        except Exception:
            pass
        return result

    @staticmethod
    def _postpaid_elapsed_minutes(holder) -> int:
        """True elapsed postpaid minutes = max(per-minute counter, wall-clock since
        start). Wall-clock matters because the counter only grows while the shell
        pings; a session started an hour before the shell connected must still show
        ~60 min, not 0."""
        base = getattr(holder, "postpaid_minutes", 0) or 0
        started = getattr(holder, "postpaid_started_at", None)
        if started:
            elapsed = int((timezone.now() - started).total_seconds() // 60)
            return max(base, elapsed)
        return base

    def check_user_access(self, user, club_id=None) -> Dict[str, Any]:
        holder = self._get_profile(user, club_id) or self.get_or_create_user_balance(user)
        blocked = self._is_blocked_in_club(user, club_id)
        if blocked:
            has_access = False  # operator block overrides everything
        elif holder.session_mode == holder.SESSION_POSTPAID:
            has_access = True  # postpaid clients always have access until operator closes
        else:
            has_access = holder.is_active and holder.minutes_remaining > 0

        # Per-club deposit + "can the client buy a tariff right now from that deposit".
        # Without this the shell only knows minutes==0 and treats a paid-up client (money
        # on deposit, no time bought yet) as "balance ended" → kicks them to login. With
        # can_buy_tariff the shell instead opens the tariffs screen so they convert
        # money → minutes themselves. Only meaningful while not already playing / blocked.
        deposit = getattr(holder, "deposit_money", None) or Decimal("0")
        can_buy_tariff = False
        if not has_access and not blocked and holder.session_mode != holder.SESSION_POSTPAID and deposit > 0:
            from apps.billing.models import TariffPlan
            cheapest = (
                TariffPlan.objects
                .filter(is_active=True, **({"club_id": club_id} if club_id else {}))
                .order_by("price")
                .values_list("price", flat=True)
                .first()
            )
            can_buy_tariff = cheapest is not None and deposit >= cheapest

        return {
            "has_access": has_access,
            "blocked": blocked,
            "session_mode": holder.session_mode,
            "minutes_remaining": holder.minutes_remaining,
            "formatted_time": holder.formatted_time,
            # Elapsed (wall-clock) so the shell's count-UP timer is correct even
            # when the shell connected long after the operator started postpaid.
            "postpaid_minutes": self._postpaid_elapsed_minutes(holder),
            # Deposit (string, like topup) + self-service-purchase signal for the shell.
            "deposit_money": str(deposit),
            "can_buy_tariff": can_buy_tariff,
        }

    # ── Postpaid ──────────────────────────────────────────────────────────────

    def start_postpaid_session(
        self,
        user_id,
        rate_per_hour: Decimal,
        admin,
        club_id=None,
    ) -> Dict[str, Any]:
        """Admin starts a postpaid session for a client.

        Switches UserBalance.session_mode to 'postpaid' and resets the debt
        counter. The client's C# shell sees has_access=True immediately.
        """
        from django.utils import timezone

        user = User.objects.get(pk=user_id)
        holder = self._get_profile(user, club_id) or self.get_or_create_user_balance(user)
        holder.session_mode = holder.SESSION_POSTPAID
        holder.postpaid_minutes = 0
        holder.postpaid_started_at = timezone.now()
        holder.postpaid_rate = Decimal(str(rate_per_hour))
        holder.is_active = True
        holder.save()
        balance = holder

        try:
            from apps.billing.models import OperationLog, LogAction
            OperationLog.objects.create(
                club_id=club_id,
                subject=admin,
                object_type="UserBalance",
                object_id=str(balance.pk),
                object_repr=f"Постоплата для {user.username} ({balance.postpaid_rate}сум/ч)",
                action=LogAction.PAYMENT_CREATE,
                payload={
                    "type": "postpaid_start",
                    "user_id": str(user.pk),
                    "rate_per_hour": str(balance.postpaid_rate),
                },
            )
        except Exception:
            pass  # non-critical audit

        # Realtime: client gets access immediately (postpaid → has_access=true).
        try:
            from realtime.broadcast import push_balance
            push_balance(user.pk, {
                "minutes_remaining": balance.minutes_remaining,
                "formatted_time": balance.formatted_time,
                "has_access": True,
                "session_mode": "postpaid",
            })
        except Exception:
            pass

        return {
            "session_mode": "postpaid",
            "user": user.username,
            "user_id": str(user.pk),
            "rate_per_hour": str(balance.postpaid_rate),
            "started_at": balance.postpaid_started_at,
        }

    def close_postpaid_session(
        self,
        user_id,
        payment_method: str,
        admin,
        club_id=None,
    ) -> Dict[str, Any]:
        """Admin closes a postpaid session: calculates cost and creates Payment.

        Returns to prepaid mode; minutes_remaining stays 0, is_active=False.
        """
        user = User.objects.get(pk=user_id)
        holder = self._get_profile(user, club_id) or self.get_or_create_user_balance(user)

        # Robust: if the club context doesn't match where postpaid actually runs
        # (operator viewing a different club, missing X-Club-Id, etc.), find the
        # user's ACTUAL active postpaid profile so closing always works.
        if holder.session_mode != holder.SESSION_POSTPAID:
            try:
                from apps.clubs.models import UserClubProfile
                # SECURITY: scope to the AUTHORIZED club — was searching every club, so an
                # operator authorized only for club A could close/bill club B's session.
                active = UserClubProfile.objects.filter(
                    user=user, club_id=club_id, session_mode="postpaid", is_active=True
                ).first()
                if active:
                    holder = active
                    club_id = active.club_id
                else:
                    bal = self.get_or_create_user_balance(user)
                    if bal.session_mode == bal.SESSION_POSTPAID:
                        holder = bal
            except Exception:
                pass

        if holder.session_mode != holder.SESSION_POSTPAID:
            raise ValueError("У пользователя нет активной постоплатной сессии")

        # Wall-clock elapsed is the source of truth for how long the PC was
        # occupied — the shell's per-minute ping can miss (crash, network drop,
        # guest never pinged). Bill the LARGER of the counter and elapsed minutes.
        minutes_played = holder.postpaid_minutes or 0
        if holder.postpaid_started_at:
            elapsed = int((timezone.now() - holder.postpaid_started_at).total_seconds() // 60)
            minutes_played = max(minutes_played, elapsed)

        rate = holder.postpaid_rate or Decimal("0")
        # Floor the rate at 0 and reject non-finite — a negative/NaN rate would
        # otherwise produce a negative/garbage Payment that poisons revenue sums.
        if not rate.is_finite() or rate < 0:
            rate = Decimal("0")
        amount = (rate * Decimal(minutes_played) / Decimal("60")).quantize(Decimal("0.01"))
        if amount < 0:
            amount = Decimal("0")

        # H4: Payment creation + profile reset MUST be atomic — a crash between them
        # left a committed Payment with the profile still in postpaid mode, so the
        # next close double-billed the same minutes.
        from django.db import transaction as _txn
        with _txn.atomic():
            # Re-lock the holder and re-check it's still postpaid. Two concurrent closes
            # (double-click, or the stop-path racing GuestPostpaidClose) both passed the
            # mode check above and double-billed; under the lock the loser sees PREPAID
            # and aborts. (Race fix verified by logic — sqlite serializes writes so it
            # can't be reproduced under load here; needs a Postgres concurrency test.)
            holder = type(holder).objects.select_for_update().get(pk=holder.pk)
            if holder.session_mode != holder.SESSION_POSTPAID:
                raise ValueError("Постоплатная сессия уже закрыта")
            payment = Payment.objects.create(
                user=user,
                admin=admin,
                amount_paid=amount,
                minutes_added=minutes_played,
                payment_method=payment_method,
                note=f"[POSTPAID] {minutes_played} мин × {rate}сум/ч",
                club_id=club_id,
            )

            # Reset back to prepaid / idle
            holder.session_mode = holder.SESSION_PREPAID
            holder.postpaid_minutes = 0
            holder.postpaid_started_at = None
            holder.postpaid_rate = None
            # Do NOT wipe minutes_remaining — a client may have topped up prepaid minutes
            # DURING the postpaid session; zeroing them lost paid time. Only the postpaid
            # debt is settled here; keep any remaining prepaid balance.
            holder.is_active = (holder.minutes_remaining or 0) > 0
            holder.save()

        # Realtime: access revoked instantly → the shell ends the session at once.
        try:
            from realtime.broadcast import push_balance
            push_balance(user.pk, {
                "minutes_remaining": 0,
                "formatted_time": "00:00",
                "has_access": False,
                "session_mode": "prepaid",
            })
        except Exception:
            pass

        return {
            "payment_id": payment.id,
            "user": user.username,
            "user_id": str(user.pk),
            "minutes_played": minutes_played,
            "amount": str(amount),
            "payment_method": payment_method,
        }

    # ── Guest postpaid (walk-in, no client account) ────────────────────────────

    @staticmethod
    def long_lived_token(user) -> str:
        """Access token that lasts a whole walk-in session. Guests have NO refresh
        token, so a 15-min default would silently break realtime (WS 403) and
        authed polls (401) mid-session. 12h covers any sitting."""
        from datetime import timedelta
        from rest_framework_simplejwt.tokens import RefreshToken
        t = RefreshToken.for_user(user).access_token
        t.set_exp(lifetime=timedelta(hours=12))
        return str(t)

    def _get_or_create_guest_user(self, computer):
        """One reusable guest account per computer: guest-pc-<id>."""
        from apps.accounts.models import CustomUser
        username = f"guest-pc-{computer.id}"
        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                "user_type": "user",
                "first_name": "Гость",
                "last_name": f"ПК-{computer.pc_number or computer.id}",
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
        return user

    def start_guest_postpaid(self, computer, rate_per_hour, admin, club_id) -> Dict[str, Any]:
        """Operator starts a walk-in postpaid session on a PC. The guest account
        plays immediately on credit; minutes accrue until the operator closes it.
        Returns a guest access token so the shell can auto-enter without a login."""
        from rest_framework_simplejwt.tokens import RefreshToken

        user = self._get_or_create_guest_user(computer)
        # A guest session ALWAYS belongs to the PC's own club, so the public
        # status endpoint (which looks up by computer.club_id) finds it. Ignore any
        # mismatching club passed from the admin's active-club selector.
        club_id = computer.club_id
        profile = self._get_profile(user, club_id)
        # Don't reset an already-running guest session — re-starting (operator double-click
        # or a forgotten session) wiped accrued unbilled minutes to 0 → lost revenue.
        # The operator must close (bill) the current session before starting a new one.
        if (profile.session_mode == profile.SESSION_POSTPAID and profile.is_active
                and profile.postpaid_started_at):
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"detail": "На этом ПК уже идёт гостевая постоплатная сессия — закройте её перед началом новой"})
        profile.is_guest = True
        profile.session_mode = profile.SESSION_POSTPAID
        profile.postpaid_minutes = 0
        profile.postpaid_started_at = timezone.now()
        profile.postpaid_rate = Decimal(str(rate_per_hour))
        profile.is_active = True
        profile.save()

        token = self.long_lived_token(user)
        return {
            "guest_user_id": str(user.pk),
            "guest_username": user.username,
            "access_token": token,
            "club_id": club_id or computer.club_id,
            "rate_per_hour": str(profile.postpaid_rate),
        }

    def close_guest_postpaid(self, computer, payment_method, admin, club_id) -> Dict[str, Any]:
        """Close the PC's guest postpaid session: bill played minutes, reset."""
        user = self._get_or_create_guest_user(computer)
        result = self.close_postpaid_session(
            user_id=user.pk, payment_method=payment_method,
            admin=admin, club_id=club_id or computer.club_id,
        )
        return result

    def transfer_guest_postpaid(self, source, target) -> Dict[str, Any]:
        """Move an active guest postpaid session from `source` PC to `target` PC,
        preserving accrued time/rate so billing continues seamlessly. The target
        shell auto-enters via its guest-status poll; the source loses access and
        returns to the lock screen. Returns None when source has no guest postpaid."""
        from apps.clubs.models import UserClubProfile
        src_user = self._get_or_create_guest_user(source)
        src = UserClubProfile.objects.filter(
            user=src_user, club_id=source.club_id,
            session_mode="postpaid", is_active=True,
        ).first()
        if not src:
            return None

        # Copy the live postpaid state onto the target's guest profile. Keeping
        # postpaid_started_at means the elapsed timer + amount due carry over.
        dst_user = self._get_or_create_guest_user(target)
        dst = self._get_profile(dst_user, target.club_id)
        # H5: move + release MUST be atomic — a crash between the two saves left BOTH
        # PCs in active postpaid, double-billing the client when each closes.
        from django.db import transaction as _txn
        with _txn.atomic():
            dst.is_guest = True
            dst.session_mode = dst.SESSION_POSTPAID
            dst.postpaid_started_at = src.postpaid_started_at
            dst.postpaid_rate = src.postpaid_rate
            dst.postpaid_minutes = src.postpaid_minutes
            dst.is_active = True
            dst.save()

            # Release the source profile (no billing — the session continues on target).
            src.session_mode = src.SESSION_PREPAID
            src.postpaid_started_at = None
            src.postpaid_rate = None
            src.postpaid_minutes = 0
            src.is_active = False
            src.save()

        # Revoke the source shell instantly (→ lock screen); the target picks the
        # session up through its guest-status poll within a few seconds.
        try:
            from realtime.broadcast import push_balance
            push_balance(src_user.pk, {
                "minutes_remaining": 0, "formatted_time": "00:00",
                "has_access": False, "session_mode": "prepaid",
            })
        except Exception:
            pass

        return {
            "moved": True,
            "from_computer": source.id,
            "to_computer": target.id,
            "rate_per_hour": str(dst.postpaid_rate),
            "started_at": dst.postpaid_started_at,
        }

    # ── Session info (client-facing) ──────────────────────────────────────────

    def get_my_session_user(self, user, club_id=None) -> Dict[str, Any]:
        """Full session info for the logged-in user. TIME is per-club when known."""
        balance = self._get_profile(user, club_id) or self.get_or_create_user_balance(user)
        payments = Payment.objects.filter(user=user).order_by("-created_at")
        last_payment = payments.first()

        session_started_at = None
        session_ends_at = None
        if last_payment:
            session_started_at = last_payment.created_at
            session_ends_at = last_payment.created_at + timezone.timedelta(
                minutes=last_payment.minutes_added
            )

        total_spent = payments.aggregate(t=Sum("amount_paid"))["t"] or Decimal("0")

        payment_history = [
            {
                "id": p.id,
                "amount_paid": str(p.amount_paid),
                "minutes_added": p.minutes_added,
                "payment_method": p.payment_method,
                "created_at": p.created_at,
                "note": p.note or "",
            }
            for p in payments[:20]
        ]

        return {
            "has_access": balance.is_active and balance.minutes_remaining > 0,
            "minutes_remaining": balance.minutes_remaining,
            "formatted_time": balance.formatted_time,
            "is_active": balance.is_active,
            "session_started_at": session_started_at,
            "session_ends_at": session_ends_at,
            "total_spent": str(total_spent),
            "visit_count": payments.count(),
            "payment_history": payment_history,
        }

    # ── Visit dynamics (client-facing) ───────────────────────────────────────

    def get_my_visits_user(self, user, year: int) -> Dict[str, Any]:
        """Monthly visit/minutes breakdown for a user."""
        payments = Payment.objects.filter(user=user, created_at__year=year).order_by(
            "created_at"
        )

        month_names = [
            "Янв",
            "Фев",
            "Мар",
            "Апр",
            "Май",
            "Июн",
            "Июл",
            "Авг",
            "Сен",
            "Окт",
            "Ноя",
            "Дек",
        ]
        visits_by_month = [0] * 12
        minutes_by_month = [0] * 12

        for p in payments:
            m = p.created_at.month - 1
            visits_by_month[m] += 1
            minutes_by_month[m] += p.minutes_added

        years = list(
            Payment.objects.filter(user=user)
            .dates("created_at", "year")
            .values_list("created_at__year", flat=True)
        )
        if not years:
            years = [year]

        peak_idx = (
            visits_by_month.index(max(visits_by_month)) if any(visits_by_month) else 0
        )

        return {
            "year": year,
            "available_years": sorted(set(years), reverse=True),
            "labels": month_names,
            "visits": visits_by_month,
            "minutes": minutes_by_month,
            "total_visits": sum(visits_by_month),
            "total_minutes": sum(minutes_by_month),
            "peak_month": month_names[peak_idx] if any(visits_by_month) else None,
        }

    # ── User list (admin-facing) ──────────────────────────────────────────────

    def list_users_with_balance(self) -> List[Dict]:
        users = User.objects.filter(user_type="user").order_by("username")
        result = []
        for u in users:
            bal = self.get_or_create_user_balance(u)
            result.append(
                {
                    "id": str(u.pk),
                    "username": u.username,
                    "minutes_remaining": bal.minutes_remaining,
                    "formatted_time": bal.formatted_time,
                    "is_active": bal.is_active,
                    "last_updated": bal.last_updated,
                }
            )
        return result

    # ── Admin stats ───────────────────────────────────────────────────────────

    def get_admin_dashboard_stats(self) -> Dict[str, Any]:
        """Aggregate stats for the admin dashboard."""
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month_start = (month_start - timezone.timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )

        # Revenue — exclude refunds ([REFUNDED] is stamped but the original positive
        # amount_paid is kept, so counting it would overstate revenue).
        revenue_qs = Payment.objects.exclude(note__icontains="[REFUNDED]")
        total_revenue = revenue_qs.aggregate(total=Sum("amount_paid"))[
            "total"
        ] or Decimal("0")
        monthly_revenue = revenue_qs.filter(created_at__gte=month_start).aggregate(
            total=Sum("amount_paid")
        )["total"] or Decimal("0")
        prev_monthly_revenue = revenue_qs.filter(
            created_at__gte=prev_month_start, created_at__lt=month_start
        ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")

        # Visits (payments = visits)
        monthly_visits = Payment.objects.filter(created_at__gte=month_start).count()
        prev_monthly_visits = Payment.objects.filter(
            created_at__gte=prev_month_start, created_at__lt=month_start
        ).count()

        # Total hours sold
        total_hours = (
            Payment.objects.aggregate(total=Sum("minutes_added"))["total"] or 0
        ) / 60

        # New clients this month
        new_clients = User.objects.filter(created_at__gte=month_start).count()
        prev_new_clients = User.objects.filter(
            created_at__gte=prev_month_start, created_at__lt=month_start
        ).count()

        # Regular clients: users with > 1 payment
        regular_clients = (
            Payment.objects.filter(user__isnull=False)
            .values("user")
            .annotate(pay_count=Count("id"))
            .filter(pay_count__gt=1)
            .count()
        )

        # Recent payments (last 10)
        recent_payments = list(
            Payment.objects.select_related("user", "admin")
            .order_by("-created_at")[:10]
            .values(
                "id",
                "user__username",
                "admin__username",
                "amount_paid",
                "minutes_added",
                "payment_method",
                "note",
                "created_at",
            )
        )

        # Hourly load: count payments per hour for the last 24h
        last_24h = now - timezone.timedelta(hours=24)
        hourly_payments = (
            Payment.objects.filter(created_at__gte=last_24h)
            .extra(select={"hour": "EXTRACT(hour FROM created_at)"})
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("hour")
        )
        hourly_data = {int(h["hour"]): h["count"] for h in hourly_payments}
        load_by_hour = [hourly_data.get(h, 0) for h in range(24)]

        # Revenue by month (last 12 months)
        revenue_by_month = self._get_monthly_revenue(12)

        # Users with active balances
        active_users = list(
            UserBalance.objects.select_related("user")
            .filter(is_active=True)
            .order_by("user__username")
            .values(
                "user__id",
                "user__username",
                "minutes_remaining",
                "is_active",
                "last_updated",
            )
        )

        def pct_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return round(float((current - previous) / previous * 100), 1)

        return {
            "total_revenue": float(total_revenue),
            "monthly_revenue": float(monthly_revenue),
            "monthly_revenue_change": pct_change(monthly_revenue, prev_monthly_revenue),
            "total_hours_played": round(total_hours, 1),
            "monthly_visits": monthly_visits,
            "monthly_visits_change": pct_change(monthly_visits, prev_monthly_visits),
            "new_clients": new_clients,
            "new_clients_change": pct_change(new_clients, prev_new_clients),
            "regular_clients": regular_clients,
            "recent_payments": recent_payments,
            "load_by_hour": load_by_hour,
            "revenue_by_month": revenue_by_month,
            "active_users": active_users,
        }

    def _get_monthly_revenue(self, months: int) -> List[Dict]:
        from django.db.models.functions import TruncMonth

        results = (
            Payment.objects.exclude(note__icontains="[REFUNDED]")
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("amount_paid"), count=Count("id"))
            .order_by("month")
        )
        return [
            {
                "month": r["month"].strftime("%b %Y") if r["month"] else "",
                "revenue": float(r["total"] or 0),
                "payments": r["count"],
            }
            for r in results
        ][-months:]

    # ── Payment history (admin-facing) ────────────────────────────────────────

    def list_payments(self) -> List[Dict]:
        rows = list(
            Payment.objects.select_related("user", "admin")
            .order_by("-created_at")
            .values(
                "id",
                "user__id",
                "user__username",
                "admin__username",
                "amount_paid",
                "minutes_added",
                "payment_method",
                "note",
                "created_at",
            )
        )
        # Rename ORM double-underscore keys to frontend-friendly names
        for row in rows:
            row["user_id"]       = row.pop("user__id", None)
            row["user_username"] = row.pop("user__username", None)
            row["admin_username"]= row.pop("admin__username", None)
        return rows
