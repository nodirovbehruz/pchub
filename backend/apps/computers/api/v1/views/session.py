from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.permissions.admin import IsAdmin
from apps.computers.models.computer import Computer
from apps.computers.models.enums import ComputerStatus


class AdminSessionStartAPIView(APIView):
    """
    POST /api/v1/computers/admin/session/start/
    Body: {
        computer_id: int,
        user_id: int | null,
        tariff_id: int | null,
        payment_method: 'cash'|'card'|'transfer'|'balance',
        amount_paid: float
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request):
        pc_id = request.data.get('computer_id')
        user_id = request.data.get('user_id')
        tariff_id = request.data.get('tariff_id')
        payment_method = request.data.get('payment_method', 'cash')
        amount_paid = float(request.data.get('amount_paid', 0) or 0)

        try:
            pc = Computer.objects.get(id=pc_id)
        except Computer.DoesNotExist:
            return Response({'error': 'ПК не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Enforce HARD bookings: can't start a session on a PC during another client's
        # hard-booking window (the hard_booking flag had no enforcement anywhere).
        try:
            from apps.bookings.models import Booking, BookingStatus
            now_ = timezone.now()
            hard = (Booking.objects.filter(
                hosts=pc, hard_booking=True,
                status__in=[BookingStatus.ACTIVE, BookingStatus.REDEEMED],
                from_at__lte=now_, to_at__gte=now_).first())
            if hard and (not user_id or str(hard.client_id) != str(user_id)):
                return Response({'error': 'ПК забронирован (жёсткая бронь) на это время'},
                                status=status.HTTP_409_CONFLICT)
        except Exception:
            pass

        # Resolve tariff
        tariff = None
        minutes = 0
        resolved_price = amount_paid

        if tariff_id:
            try:
                from apps.billing.models import TariffPlan, PricePeriod
                tariff = TariffPlan.objects.prefetch_related('prices').get(id=tariff_id)
                minutes = tariff.minutes

                now = timezone.localtime()
                hour = now.hour
                period = PricePeriod.NIGHT if (hour >= 22 or hour < 8) else PricePeriod.DAY

                # Setting: «Праздничный тариф» — on holiday dates charge the NIGHT
                # (special) price all day. holiday_dates: list of "DD.MM" or "DD.MM.YYYY".
                try:
                    from apps.clubs.models import ClubSettings
                    if ClubSettings.get_bool(pc.club_id, 'holiday_tariff', False):
                        hd = ClubSettings.get_value(pc.club_id, 'holiday_dates', []) or []
                        today_md = now.strftime('%d.%m')
                        today_full = now.strftime('%d.%m.%Y')
                        if today_md in hd or today_full in hd:
                            period = PricePeriod.NIGHT
                except Exception:
                    pass

                if pc.group_id:
                    tp = tariff.prices.filter(group_id=pc.group_id, period=period).first() \
                         or tariff.prices.filter(group_id=pc.group_id).first()
                    if tp:
                        resolved_price = float(tp.price)

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

        # Pay «С баланса» = use the client's EXISTING per-club time, which the
        # per-minute deduction consumes during play. Do NOT deduct the tariff minutes
        # upfront (that would double-charge) and do NOT touch the legacy global
        # UserBalance (the shell never reads it). Just verify they actually have time.
        if target_user and payment_method == 'balance':
            from apps.billing.services.implementation.billing import BillingService
            _svc = BillingService()
            _holder = _svc._get_profile(target_user, pc.club_id) or _svc.get_or_create_user_balance(target_user)
            if (_holder.minutes_remaining or 0) <= 0:
                return Response(
                    {'error': 'У клиента нет времени на балансе'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Record payment for cash/card/transfer
        if payment_method in ('cash', 'card', 'transfer') and request.user.is_authenticated:
            from apps.billing.models import Payment, PaymentMethod
            method_map = {
                'cash': PaymentMethod.CASH,
                'card': PaymentMethod.CARD,
                'transfer': PaymentMethod.TRANSFER,
            }
            Payment.objects.create(
                user=target_user,
                computer=pc,
                admin=request.user,
                amount_paid=resolved_price,
                minutes_added=minutes,
                payment_method=method_map.get(payment_method, PaymentMethod.CASH),
                club_id=pc.club_id,
            )
            # BUGFIX: previously the Payment was recorded but the purchased TIME was
            # never credited anywhere, so a registered client paid cash/card and got
            # 0 playable minutes. Credit the minutes to the PER-CLUB profile (the
            # ledger the shell reads via /billing/balance → check_user_access), and
            # push the new balance so the shell unlocks instantly.
            if target_user and minutes > 0:
                try:
                    from apps.billing.services.implementation.billing import BillingService
                    profile = BillingService._get_profile(target_user, pc.club_id)
                    holder = profile or BillingService().get_or_create_user_balance(target_user)
                    holder.add_minutes(minutes)
                    from realtime.broadcast import push_balance
                    push_balance(target_user.pk, {
                        "minutes_remaining": holder.minutes_remaining,
                        "formatted_time": holder.formatted_time,
                        "has_access": bool(holder.is_active and holder.minutes_remaining > 0),
                        "session_mode": getattr(holder, "session_mode", "prepaid"),
                    })
                except Exception:
                    pass

        # Guest session if no user
        if not target_user:
            from apps.computers.models import GuestSession
            GuestSession.objects.filter(computer=pc, is_active=True).update(
                is_active=False, end_time=timezone.now()
            )
            GuestSession.objects.create(
                computer=pc,
                rate_per_hour=resolved_price * 60 / max(minutes, 1) if minutes else 0,
                total_amount=resolved_price,
                notes=f"Tariff: {tariff.name if tariff else 'manual'}",
            )

        # Set PC online
        pc.status = ComputerStatus.ONLINE
        pc.save(update_fields=['status'])

        # Audit log
        from apps.billing.services.audit import log_action
        from apps.billing.models import LogAction
        client_label = target_user.username if target_user else "Гость"
        log_action(
            request, LogAction.SESSION_START, obj=pc,
            object_type="Computer",
            repr_=f"{pc.name}: сеанс начат ({client_label})",
            payload={
                "computer": pc.name,
                "client": client_label,
                "tariff": tariff.name if tariff else None,
                "minutes": minutes,
                "amount": str(resolved_price),
            },
        )

        return Response({
            'success': True,
            'message': 'Сеанс успешно начат',
            'computer_id': pc.id,
            'status': pc.status,
        }, status=status.HTTP_200_OK)


class AdminSessionStopAPIView(APIView):
    """
    POST /api/v1/computers/admin/session/stop/
    Body: {computer_id: int}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        pc_id = request.data.get('computer_id')
        try:
            pc = Computer.objects.get(id=pc_id)
        except Computer.DoesNotExist:
            return Response({'error': 'ПК не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Fleet control is allowed to the club owner / manager / platform admin —
        # not only a platform admin (so the owner can end sessions on their PCs).
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({'error': 'Нет прав на управление этим ПК'}, status=status.HTTP_403_FORBIDDEN)

        pc.status = ComputerStatus.OFFLINE
        pc.save(update_fields=['status'])

        # Close any active guest session
        from apps.computers.models import GuestSession
        GuestSession.objects.filter(computer=pc, is_active=True).update(
            is_active=False, end_time=timezone.now()
        )

        # If a guest POSTPAID session is running on this PC, close it (bills the
        # played minutes, cash) so "Завершить сеанс" actually ends postpaid too.
        billed = None
        try:
            from apps.billing.services.implementation.billing import BillingService
            from apps.accounts.models import CustomUser
            from apps.clubs.models import UserClubProfile
            guest = CustomUser.objects.filter(username=f"guest-pc-{pc.id}").first()
            if guest and UserClubProfile.objects.filter(
                user=guest, club_id=pc.club_id, session_mode="postpaid", is_active=True
            ).exists():
                pay_method = request.data.get("payment_method") or "cash"
                if pay_method not in ("cash", "card", "transfer"):
                    pay_method = "cash"
                billed = BillingService().close_guest_postpaid(
                    computer=pc, payment_method=pay_method, admin=u, club_id=pc.club_id,
                )
        except Exception:
            pass

        # Terminate a REAL logged-in client at this PC (not the synthetic guest).
        # Was a no-op for normal logins: the shell kept its JWT, kept deducting time
        # and playing, and its heartbeat reverted pc.status to ONLINE. Mirror the
        # transfer path — revoke access (so the shell logs out) + LOCK the shell.
        try:
            from apps.accounts.models import CustomUser
            from apps.computers.models import ComputerCommand
            from apps.computers.models.command import CommandType, CommandStatus
            ended_clients = []
            if pc.hardware_id:
                ended_clients = list(CustomUser.objects.filter(
                    active_hardware_id=pc.hardware_id, is_active_session=True,
                ))
            for cu in ended_clients:
                cu.is_active_session = False
                cu.active_hardware_id = ""
                cu.save(update_fields=["is_active_session", "active_hardware_id"])
                # Finish any ACTIVE billing session for this client on this PC.
                try:
                    from apps.sessions_.models import ClientSession, ClientSessionStatus
                    ClientSession.objects.filter(
                        client=cu, status=ClientSessionStatus.ACTIVE, hosts__computer=pc,
                    ).update(status=ClientSessionStatus.FINISHED, finished_at=timezone.now())
                except Exception:
                    pass
                # Realtime revoke → shell raises AccessRevoked (kills games + logout).
                try:
                    from realtime.broadcast import push_balance
                    push_balance(cu.pk, {
                        "minutes_remaining": 0, "formatted_time": "00:00",
                        "has_access": False, "session_mode": "prepaid",
                    })
                except Exception:
                    pass
            if ended_clients:
                # Belt-and-suspenders lock even if the WS push is missed.
                ComputerCommand.objects.create(
                    computer=pc, command_type=CommandType.LOCK,
                    status=CommandStatus.PENDING, payload={}, created_by=u,
                )
        except Exception:
            pass

        # Audit log
        from apps.billing.services.audit import log_action
        from apps.billing.models import LogAction
        log_action(
            request, LogAction.SESSION_END, obj=pc,
            object_type="Computer",
            repr_=f"{pc.name}: сеанс завершён",
            payload={"computer": pc.name},
        )

        msg = 'Сеанс завершён'
        if billed:
            msg = f"Сеанс завершён. Постоплата: {billed.get('minutes_played', 0)} мин, {billed.get('amount', '0')} сум"
        return Response({'success': True, 'message': msg, 'billed': billed})


class AdminSessionTransferAPIView(APIView):
    """
    POST /api/v1/computers/admin/session/transfer/
    Body: {source_computer_id|computer_id: int, target_computer_id|target: int}

    Moves an ACTIVE session (currently: guest postpaid) from one PC to another in
    the same club, preserving accrued time/rate. The source PC is locked back to
    the login screen; the target picks the session up via its guest-status poll.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        src_id = request.data.get('source_computer_id') or request.data.get('computer_id')
        dst_id = request.data.get('target_computer_id') or request.data.get('target')
        if not src_id or not dst_id:
            return Response({'error': 'Нужны source_computer_id и target_computer_id'},
                            status=status.HTTP_400_BAD_REQUEST)
        if str(src_id) == str(dst_id):
            return Response({'error': 'Исходный и целевой ПК совпадают'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            src = Computer.objects.get(id=src_id)
            dst = Computer.objects.get(id=dst_id)
        except Computer.DoesNotExist:
            return Response({'error': 'ПК не найден'}, status=status.HTTP_404_NOT_FOUND)

        if src.club_id != dst.club_id:
            return Response({'error': 'Перенос возможен только внутри одного клуба'},
                            status=status.HTTP_400_BAD_REQUEST)

        # Owner / manager / platform admin of the club may transfer.
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=src.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=src.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({'error': 'Нет прав на управление этими ПК'},
                                status=status.HTTP_403_FORBIDDEN)

        # Target must be free (no active guest postpaid of its own).
        from apps.accounts.models import CustomUser
        from apps.clubs.models import UserClubProfile
        from apps.computers.models import ComputerCommand, GuestSession
        from apps.computers.models.command import CommandType, CommandStatus
        dst_guest = CustomUser.objects.filter(username=f"guest-pc-{dst.id}").first()
        if dst_guest and UserClubProfile.objects.filter(
            user=dst_guest, club_id=dst.club_id, session_mode="postpaid", is_active=True
        ).exists():
            return Response({'error': 'Целевой ПК уже занят'}, status=status.HTTP_400_BAD_REQUEST)

        # Move the guest postpaid session (preserves accrued time/rate).
        from apps.billing.services.implementation.billing import BillingService
        moved = BillingService().transfer_guest_postpaid(source=src, target=dst)

        # Move any GuestSession bookkeeping row too.
        GuestSession.objects.filter(computer=src, is_active=True).update(computer=dst)

        if not moved:
            return Response({'error': 'На исходном ПК нет активной сессии для переноса'},
                            status=status.HTTP_400_BAD_REQUEST)

        # PC statuses follow the real session.
        src.status = ComputerStatus.OFFLINE; src.save(update_fields=['status'])
        dst.status = ComputerStatus.ONLINE; dst.save(update_fields=['status'])

        # Lock the source shell immediately (belt-and-suspenders alongside the
        # access-revoke push); the target auto-enters via its guest-status poll.
        ComputerCommand.objects.create(
            computer=src, command_type=CommandType.LOCK,
            status=CommandStatus.PENDING, payload={}, created_by=u,
        )

        # Audit log
        from apps.billing.services.audit import log_action
        from apps.billing.models import LogAction
        log_action(
            request, LogAction.SESSION_START, obj=dst, object_type="Computer",
            repr_=f"Перенос сеанса: {src.name} → {dst.name}",
            payload={"from": src.name, "to": dst.name},
        )

        return Response({
            'success': True,
            'message': f'Клиент перенесён: {src.name} → {dst.name}',
            'transfer': moved,
        })


class AdminNotifyAPIView(APIView):
    """
    POST /api/v1/computers/admin/notify/
    Body: {computer_id: int, text: str, title?: str}

    Sends a realtime notification to whoever is currently sitting at the PC
    (guest session or logged-in client) — shown instantly in the shell.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        pc_id = request.data.get('computer_id') or request.data.get('computer')
        text = (request.data.get('text') or '').strip()
        title = (request.data.get('title') or 'Сообщение от администратора').strip()
        if not text:
            return Response({'error': 'Пустой текст'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pc = Computer.objects.get(id=pc_id)
        except Computer.DoesNotExist:
            return Response({'error': 'ПК не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Owner / manager / platform admin of the PC's club.
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({'error': 'Нет прав на этот ПК'}, status=status.HTTP_403_FORBIDDEN)

        # Resolve who is at the PC: a logged-in client (active_hardware_id) or the
        # per-PC guest account. Notify all that match (best-effort).
        from apps.accounts.models import CustomUser
        targets = set()
        guest = CustomUser.objects.filter(username=f"guest-pc-{pc.id}").first()
        if guest:
            targets.add(guest.pk)
        if pc.hardware_id:
            for cu in CustomUser.objects.filter(active_hardware_id=pc.hardware_id, is_active_session=True):
                targets.add(cu.pk)

        delivered = 0
        try:
            from realtime.broadcast import push_notify
            for uid in targets:
                push_notify(uid, {"title": title, "message": text})
                delivered += 1
        except Exception:
            pass

        return Response({'success': True, 'delivered': delivered,
                         'message': 'Уведомление отправлено' if delivered else 'Никто не за ПК — некому доставить'})


class AdminSessionFineAPIView(APIView):
    """
    POST /api/v1/computers/admin/session/fine/
    Body: {computer_id: int, minutes: int}

    Penalty: docks `minutes` from the client currently at the PC. Time is AUTHORITATIVE
    on the backend, so this deducts from the per-club profile the shell reads (was a
    dead 'fine' command the backend rejected and the shell never handled).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        pc_id = request.data.get('computer_id') or request.data.get('computer')
        try:
            minutes = int(request.data.get('minutes', 0) or 0)
        except (TypeError, ValueError):
            minutes = 0
        if minutes <= 0:
            return Response({'error': 'minutes must be > 0'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            pc = Computer.objects.get(id=pc_id)
        except Computer.DoesNotExist:
            return Response({'error': 'ПК не найден'}, status=status.HTTP_404_NOT_FOUND)

        # Owner / manager / platform admin of the PC's club.
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({'error': 'Нет прав на этот ПК'}, status=status.HTTP_403_FORBIDDEN)

        # Resolve the client at this PC (logged-in client, else per-PC guest).
        from apps.accounts.models import CustomUser
        from django.db import transaction as _txn
        target = None
        if pc.hardware_id:
            target = CustomUser.objects.filter(active_hardware_id=pc.hardware_id, is_active_session=True).first()
        if target is None:
            target = CustomUser.objects.filter(username=f"guest-pc-{pc.id}").first()
        if target is None:
            return Response({'error': 'Никто не за ПК'}, status=status.HTTP_400_BAD_REQUEST)

        from apps.billing.services.implementation.billing import BillingService
        svc = BillingService()
        with _txn.atomic():
            profile = svc._get_profile(target, pc.club_id)
            base = profile or svc.get_or_create_user_balance(target)
            # A minute-fine only applies to PREPAID time. On a POSTPAID session
            # minutes_remaining is 0 → the deduction is a no-op, AND the realtime push
            # below would compute has_access from minutes_remaining=0 and wrongly KICK
            # the postpaid client. Reject with a clear message instead.
            if getattr(base, "session_mode", "prepaid") == getattr(base, "SESSION_POSTPAID", "postpaid"):
                return Response({'error': 'Штраф в минутах неприменим к постоплатной сессии'},
                                status=status.HTTP_400_BAD_REQUEST)
            # Lock the row before mutating (deduct can't go below zero).
            holder = base.__class__.objects.select_for_update().get(pk=base.pk)
            holder.minutes_remaining = max(0, (holder.minutes_remaining or 0) - minutes)
            holder.save(update_fields=['minutes_remaining'])

        # Push the new balance so the shell reflects the penalty instantly.
        try:
            from realtime.broadcast import push_balance
            push_balance(target.pk, {
                "minutes_remaining": holder.minutes_remaining,
                "formatted_time": holder.formatted_time,
                "has_access": bool(holder.is_active and holder.minutes_remaining > 0),
                "session_mode": getattr(holder, "session_mode", "prepaid"),
            })
        except Exception:
            pass

        # Audit
        try:
            from apps.billing.services.audit import log_action
            from apps.billing.models import LogAction
            log_action(
                request, LogAction.SESSION_PENALIZE, obj=pc, object_type="Computer",
                repr_=f"{pc.name}: штраф −{minutes} мин",
                payload={"minutes": minutes, "client": target.username},
            )
        except Exception:
            pass

        return Response({'success': True, 'minutes_deducted': minutes,
                         'minutes_remaining': holder.minutes_remaining})
