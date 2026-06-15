from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.computers.api.v1.serializers.computer import (
    ComputerRegistrationSerializer,
    ComputerSerializer,
)
from apps.computers.api.v1.serializers.computer_game import ComputerGameSerializer
from apps.computers.models import Computer
from apps.computers.repositories.implementation.computer import ComputerRepository
from apps.computers.services.implementation.computer import ComputerService
from apps.computers.services.implementation.computer_game import ComputerGameService


@extend_schema(tags=["Computers"])
class ComputerRegistrationAPIView(generics.CreateAPIView):
    """
    Register a new computer from C# app

    POST endpoint for C# application to register a new computer.

    Example C# request:
    ```json
    {
        "name": "Gaming-PC-01",
        "description": "Main gaming computer",
        "cpu_model": "Intel Core i7-12700K",
        "cpu_cores": 12,
        "cpu_threads": 20,
        "ram_total_gb": 32.0,
        "gpu_model": "NVIDIA RTX 3080",
        "storage_total_gb": 1000.0,
        "os_name": "Windows",
        "os_version": "11 Pro",
        "ip_address": "192.168.1.100",
        "mac_address": "00:11:22:33:44:55"
    }
    ```
    """

    serializer_class = ComputerRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    service = ComputerService(repository=ComputerRepository())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set owner to current user if authenticated and not provided
        data = serializer.validated_data.copy()
        if "owner_id" not in data and request.user.is_authenticated:
            data["owner_id"] = request.user.id
        elif "owner_id" not in data:
            data["owner_id"] = None

        # Auto-link to club via club_token if provided.
        club_token = data.pop("club_token", None)
        if club_token:
            from apps.clubs.models import Club
            club = Club.objects.filter(club_token=club_token.upper().strip()).first()
            if club:
                data["club_id"] = club.id
            # else: an INVALID token must NOT hard-fail — an existing PC (matched by
            # hardware_id) re-registers and keeps its current club so its heartbeat
            # keeps working. A brand-new PC with no resolvable club is rejected inside
            # register_computer(). (A hard 400 here previously broke heartbeat for any
            # PC whose stored club_token had gone stale → it showed offline.)

        # Register computer
        computer = self.service.register_computer(data)

        # Return computer data
        response_serializer = ComputerSerializer(computer)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Computers"])
class ComputerListAPIView(generics.ListAPIView):
    """
    Get list of all computers

    Optionally filter by owner (authenticated user's computers)
    """

    serializer_class = ComputerSerializer
    permission_classes = [permissions.IsAuthenticated]
    service = ComputerService()

    def post(self, request, *args, **kwargs):
        """Admin creates a PC manually. Goes through register_computer so the
        club's subscription PC-limit (max_pcs) is enforced here too."""
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"name": "Введите название"}, status=status.HTTP_400_BAD_REQUEST)
        club_id = (request.data.get("club") or request.data.get("club_id")
                   or getattr(request, "current_club_id", None))
        if not club_id:
            return Response({"club": "Не указан клуб"}, status=status.HTTP_400_BAD_REQUEST)

        # Tenant guard: only the club's owner/manager (or platform admin) may add a PC
        # to it — don't trust the club id from the body blindly.
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({"error": "Нет прав на этот клуб"}, status=status.HTTP_403_FORBIDDEN)

        data = {"name": name, "club_id": club_id}
        group = request.data.get("group")
        if group:
            data["group_id"] = group
        # register_computer raises DRF ValidationError (→ 400) if the PC limit is hit.
        computer = self.service.register_computer(data)
        return Response(ComputerSerializer(computer).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = Computer.objects.filter(is_active=True).select_related("group", "owner")

        # SECURITY: ClubTenantMiddleware sets current_club_id from ?club= BEFORE JWT
        # auth (request.user is anonymous in middleware), so it does NOT prove
        # membership — a non-member passing ?club=<victim> would otherwise list that
        # club's PCs. Here in the DRF view request.user IS authenticated, so we
        # verify membership explicitly against the real user.
        user = self.request.user
        is_platform_admin = getattr(user, "user_type", "") == "admin"
        mine = self.request.query_params.get("my_computers") == "true"
        club_id = getattr(self.request, "current_club_id", None) or self.request.query_params.get("club")

        if is_platform_admin:
            if club_id:
                queryset = queryset.filter(club_id=club_id)
        elif club_id:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=club_id, owner=user).exists() or ClubMembership.objects.filter(
                user=user, club_id=club_id, is_active=True
            ).exists()
            if not allowed:
                return queryset.none()  # not a member of the requested club
            queryset = queryset.filter(club_id=club_id)
        elif mine:
            queryset = queryset.filter(owner=user)
        else:
            return queryset.none()  # no club context → nothing

        group_id = self.request.query_params.get("group")
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        if mine:
            queryset = queryset.filter(owner=user)

        return queryset.order_by("pc_number", "name")

    def list(self, request, *args, **kwargs):
        """Bulk-compute session/booking/game maps in O(1) queries to avoid N+1."""
        from django.db.models import Count, Sum

        pcs = list(self.filter_queryset(self.get_queryset()))
        pc_ids = [p.id for p in pcs]
        ctx = self.get_serializer_context()

        if pc_ids:
            # 1) Installed games count per PC
            try:
                from apps.computers.models.computer_game import ComputerGame as _IG
                games_count = {
                    r["computer_id"]: r["n"] for r in
                    _IG.objects.filter(computer_id__in=pc_ids, is_installed=True)
                    .values("computer_id").annotate(n=Count("id"))
                }
            except Exception:
                games_count = {}
            ctx["games_count_map"] = games_count

            # 2) Total gaming hours per PC
            try:
                from apps.games.models.session import GameSession as _GS
                hours = {
                    r["computer_id"]: float(r["t"] or 0) for r in
                    _GS.objects.filter(computer_id__in=pc_ids)
                    .values("computer_id").annotate(t=Sum("total_hours_played"))
                }
            except Exception:
                hours = {}
            ctx["gaming_hours_map"] = hours

            # 3) Active sessions per PC (single query via SessionHost)
            try:
                from apps.sessions_.models import ClientSessionStatus
                from apps.sessions_.models.client_session import SessionHost
                sess_map = {}
                for sh in (
                    SessionHost.objects
                    .filter(computer_id__in=pc_ids, session__status=ClientSessionStatus.ACTIVE)
                    .select_related("session", "session__client", "session__tariff")
                ):
                    sess_map.setdefault(sh.computer_id, sh.session)

                # Guest postpaid sessions don't create a ClientSession — they live
                # as UserClubProfile(session_mode=postpaid) on a "guest-pc-<id>"
                # user. Surface them so the PC shows as occupied and the admin can
                # end the session (otherwise "Завершить сеанс" stays disabled).
                from apps.clubs.models import UserClubProfile
                from django.utils import timezone as _tz
                guest_usernames = {f"guest-pc-{pid}": pid for pid in pc_ids}
                for prof in (
                    UserClubProfile.objects
                    .filter(user__username__in=list(guest_usernames),
                            session_mode="postpaid", is_active=True)
                    .select_related("user")
                ):
                    pid = guest_usernames.get(prof.user.username)
                    if pid is None or pid in sess_map:
                        continue
                    started = prof.postpaid_started_at
                    mins = int((_tz.now() - started).total_seconds() / 60) if started else 0
                    # Live cost = rate × elapsed (wall-clock), so the cashier sees
                    # the running amount due before closing the session.
                    rate = prof.postpaid_rate or 0
                    from decimal import Decimal as _D
                    amount_due = str((_D(str(rate)) * _D(mins) / _D("60")).quantize(_D("0.01")))
                    sess_map[pid] = {
                        "id": f"postpaid-{pid}",
                        "client": "Гость (постоплата)",
                        "tariff": "Постоплата",
                        "started_at": started,
                        "time_left_minutes": None,
                        "is_postpaid": True,
                        "minutes_played": mins,
                        "postpaid_rate": str(rate),
                        "amount_due": amount_due,
                    }
                ctx["active_sessions_map"] = sess_map
            except Exception:
                ctx["active_sessions_map"] = {}

            # 4) Next booking per PC (single query)
            try:
                from apps.bookings.models import Booking, BookingStatus
                from django.utils import timezone
                ids_set = set(pc_ids)
                booking_map = {}
                for b in (
                    Booking.objects
                    .filter(hosts__id__in=pc_ids, status=BookingStatus.ACTIVE, to_at__gte=timezone.now())
                    .order_by("from_at").select_related("client").prefetch_related("hosts")
                ):
                    for h in b.hosts.all():
                        if h.id in ids_set and h.id not in booking_map:
                            booking_map[h.id] = b
                ctx["bookings_map"] = booking_map
            except Exception:
                ctx["bookings_map"] = {}

        serializer = self.get_serializer(pcs, many=True, context=ctx)
        return Response(serializer.data)


@extend_schema(tags=["Computers"])
class ComputerPositionUpdateAPIView(APIView):
    """Update PC map position via drag&drop (technical mode).

    Also accepts `status` to toggle MAINTENANCE/ONLINE/etc from the map UI.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, computer_id):
        from apps.computers.models import ComputerStatus
        try:
            pc = Computer.objects.get(id=computer_id)
        except Computer.DoesNotExist:
            return Response({"error": "PC not found"}, status=status.HTTP_404_NOT_FOUND)

        # SECURITY: verify the requester manages this PC's club — without this any
        # authenticated user could move/maintenance another club's PCs (IDOR).
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({"error": "Нет прав на этот ПК"}, status=status.HTTP_403_FORBIDDEN)

        x = request.data.get("position_x")
        y = request.data.get("position_y")
        group_id = request.data.get("group")
        new_status = request.data.get("status")
        update_fields = ["updated_at"]
        if x is not None:
            pc.position_x = int(x)
            update_fields.append("position_x")
        if y is not None:
            pc.position_y = int(y)
            update_fields.append("position_y")
        if group_id is not None:
            pc.group_id = group_id or None
            update_fields.append("group")
        if new_status is not None:
            valid = {s.value for s in ComputerStatus}
            if new_status not in valid:
                return Response(
                    {"error": f"invalid status; allowed: {sorted(valid)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pc.status = new_status
            update_fields.append("status")
        pc.save(update_fields=update_fields)
        return Response({
            "id": pc.id, "position_x": pc.position_x, "position_y": pc.position_y,
            "group": pc.group_id, "status": pc.status,
        })


@extend_schema(tags=["Computers"])
class ComputerDetailAPIView(APIView):
    """
    Get computer overview with statistics and installed games list
    """

    permission_classes = [permissions.IsAuthenticated]
    service = ComputerService()
    game_service = ComputerGameService()

    def get(self, request, computer_id):
        # SECURITY: was no club scoping — any authenticated user could read any
        # club's PC detail by guessing the computer_id (IDOR on read path).
        # Verify the requester has access to this PC's club before proceeding.
        try:
            pc = Computer.objects.get(id=computer_id)
        except Computer.DoesNotExist:
            return Response({"error": "ПК не найден"}, status=status.HTTP_404_NOT_FOUND)
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True
            ).exists()
            if not allowed:
                return Response({"error": "Нет прав на этот ПК"}, status=status.HTTP_403_FORBIDDEN)

        # Get computer overview
        data = self.service.get_computer_overview(computer_id)

        # Get installed games
        games_data = self.game_service.get_installed_games(
            computer_id=computer_id, installed_only=True
        )

        # Serialize data
        computer_serializer = ComputerSerializer(data["computer"])
        installed_games_serializer = ComputerGameSerializer(
            games_data["installed_games"], many=True
        )

        return Response(
            {
                "computer": computer_serializer.data,
                "installed_games_count": data["installed_games_count"],
                "total_gaming_hours": data["total_gaming_hours"],
                "total_games_size_gb": games_data["total_size_gb"],
                "latest_metrics": data["latest_metrics"],
                "status": data["status"],
                "last_seen": data["last_seen"],
                "installed_games": installed_games_serializer.data,
            }
        )

    def _pc_if_allowed(self, request, computer_id):
        """Return (pc, None) if the user may manage this PC, else (None, Response)."""
        try:
            pc = Computer.objects.get(id=computer_id)
        except Computer.DoesNotExist:
            return None, Response({"error": "ПК не найден"}, status=status.HTTP_404_NOT_FOUND)
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return None, Response({"error": "Нет прав на этот ПК"}, status=status.HTTP_403_FORBIDDEN)
        return pc, None

    def patch(self, request, computer_id):
        """Admin edits a PC (name / group). Owner / manager / platform admin only."""
        pc, err = self._pc_if_allowed(request, computer_id)
        if err:
            return err
        fields = []
        if "name" in request.data:
            name = (request.data.get("name") or "").strip()
            if not name:
                return Response({"name": "Введите название"}, status=status.HTTP_400_BAD_REQUEST)
            pc.name = name; fields.append("name")
        if "group" in request.data:
            pc.group_id = request.data.get("group") or None; fields.append("group_id")
        if fields:
            pc.save(update_fields=fields)
        return Response(ComputerSerializer(pc).data)

    def delete(self, request, computer_id):
        """Soft-delete a PC (is_active=False) so it frees the club's subscription
        PC-limit slot. Owner / manager / platform admin only."""
        pc, err = self._pc_if_allowed(request, computer_id)
        if err:
            return err
        pc.is_active = False
        pc.save(update_fields=["is_active"])
        return Response({"success": True, "message": f"ПК «{pc.name}» удалён (освобождён слот тарифа)."})


@extend_schema(tags=["Computers"])
class ComputerUpdateSpecsAPIView(generics.UpdateAPIView):
    """
    Update computer hardware specifications from C# app
    """

    serializer_class = ComputerRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]
    service = ComputerService()

    def update(self, request, computer_id):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Update specs
        computer = self.service.update_computer_specs(
            computer_id=computer_id, data=serializer.validated_data
        )

        # Return updated computer
        response_serializer = ComputerSerializer(computer)
        return Response(response_serializer.data)


@extend_schema(tags=["Computers"])
class ComputerHeartbeatAPIView(APIView):
    """
    Send heartbeat to keep computer status ONLINE

    Called every 30 seconds from the C# shell to indicate the PC is running —
    INCLUDING while it sits at the login screen (no client logged in), so a
    powered-on PC shows online to the operator. It is therefore unauthenticated
    and identifies the PC purely by the URL computer_id. authentication_classes=[]
    so a stale shell Bearer token can't trigger a 401 on this AllowAny endpoint.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    service = ComputerService()

    def post(self, request, computer_id):
        result = self.service.heartbeat(computer_id=computer_id)
        return Response(result)


@extend_schema(tags=["Computers"])
class ComputerHighAccessAPIView(APIView):
    """Admin: grant/revoke HIGH-ACCESS (elevated desktop) on a PC.

    POST /api/v1/computers/<pk>/high-access/  body: { "enabled": true|false }
    Toggles `computer.high_access_active` and enqueues a `high_access` /
    `high_access_off` command for the shell to apply (drop kiosk lockdown +
    restore the Windows shell on grant; re-lock on revoke).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.computers.models import ComputerCommand
        try:
            pc = Computer.objects.get(pk=pk)
        except Computer.DoesNotExist:
            return Response({"error": "ПК не найден"}, status=status.HTTP_404_NOT_FOUND)

        # SECURITY: owner / manager of the PC's club, or platform admin (IDOR guard).
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=pc.club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=pc.club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({"error": "Нет прав на этот ПК"}, status=status.HTTP_403_FORBIDDEN)

        enabled = bool(request.data.get("enabled", not pc.high_access_active))

        # Pass the club's high-access password so the shell can apply it if needed.
        password = ""
        try:
            from apps.integrations.models.shell_security import ShellSecurity
            sec = ShellSecurity.objects.filter(club_id=pc.club_id).first()
            if sec:
                password = sec.high_access_password or ""
        except Exception:
            pass

        pc.high_access_active = enabled
        pc.save(update_fields=["high_access_active", "updated_at"])

        ComputerCommand.objects.create(
            computer=pc,
            command_type="high_access" if enabled else "high_access_off",
            payload={"password": password} if enabled else {},
            created_by=request.user,
        )

        # Audit
        try:
            from apps.billing.services.audit import log_action
            from apps.billing.models import LogAction
            log_action(
                request, LogAction.PC_HIGH_ACCESS, obj=pc, object_type="Computer",
                club_id=getattr(pc, "club_id", None),
                repr_=f"{pc.name}: высокий доступ {'включён' if enabled else 'выключен'}",
                payload={"high_access": enabled},
            )
        except Exception:
            pass

        return Response({
            "id": pc.id,
            "high_access_active": pc.high_access_active,
            "message": f"Высокий доступ {'включён' if enabled else 'выключен'} для «{pc.name}»",
        })
