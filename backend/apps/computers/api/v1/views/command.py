from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.v1.permissions.admin import IsAdmin
from apps.computers.api.v1.serializers.command import (
    ComputerCommandCreateSerializer,
    ComputerCommandSerializer,
    ComputerCommandStatusUpdateSerializer,
)
from apps.computers.models import Computer, ComputerCommand
from apps.computers.models.command import CommandStatus
from apps.games.models import Game


@extend_schema(tags=["Admin - Software Management"])
class AdminCommandListCreateAPIView(APIView):
    """
    Admin: list all commands or create a new install/uninstall/update command for a PC.
    """

    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _can_manage(user, club_id):
        """Club owner / manager / platform admin may command a club's PCs."""
        if getattr(user, "is_admin", False) or getattr(user, "user_type", "") == "admin":
            return True
        if not club_id:
            return False
        from apps.clubs.models import Club, ClubMembership
        return Club.objects.filter(id=club_id, owner=user).exists() or ClubMembership.objects.filter(
            user=user, club_id=club_id, is_active=True, role__in=["owner", "manager"]
        ).exists()

    def get(self, request):
        computer_id = request.query_params.get("computer_id")
        qs = ComputerCommand.objects.select_related("computer", "game", "created_by")
        if computer_id:
            qs = qs.filter(computer_id=computer_id)
        serializer = ComputerCommandSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ComputerCommandCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            computer = Computer.objects.get(pk=data["computer_id"])
        except Computer.DoesNotExist:
            return Response(
                {"detail": "Computer not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Owner/manager of the PC's club (or platform admin) — not only platform admin.
        if not self._can_manage(request.user, getattr(computer, "club_id", None)):
            return Response(
                {"detail": "Нет прав на управление этим ПК."},
                status=status.HTTP_403_FORBIDDEN,
            )

        game = None
        if data.get("game_id"):
            try:
                game = Game.objects.get(pk=data["game_id"])
            except Game.DoesNotExist:
                return Response(
                    {"detail": "Game not found."}, status=status.HTTP_404_NOT_FOUND
                )

        command = ComputerCommand.objects.create(
            computer=computer,
            game=game,
            command_type=data["command_type"],
            payload=data.get("payload", {}),
            created_by=request.user,
        )

        # Audit log — power commands
        try:
            from apps.billing.services.audit import log_action
            from apps.billing.models import LogAction
            ct = data["command_type"]
            power_map = {
                "reboot":    (LogAction.PC_REBOOT,    "перезагрузка"),
                "restart":   (LogAction.PC_REBOOT,    "перезагрузка"),
                "shutdown":  (LogAction.PC_POWER_OFF, "выключение"),
                "power_off": (LogAction.PC_POWER_OFF, "выключение"),
                "power_on":  (LogAction.PC_POWER_ON,  "включение"),
                "wake":      (LogAction.PC_POWER_ON,  "включение"),
            }
            if ct in power_map:
                action, label = power_map[ct]
                log_action(
                    request, action, obj=computer, object_type="Computer",
                    club_id=getattr(computer, "club_id", None),
                    repr_=f"{computer.name}: {label}",
                    payload={"command": ct, "computer": computer.name},
                )
        except Exception:
            pass

        return Response(
            ComputerCommandSerializer(command).data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Admin - Software Management"])
class AdminCommandCancelAPIView(APIView):
    """Admin: cancel a pending command."""

    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def delete(self, request, command_id):
        try:
            command = ComputerCommand.objects.get(pk=command_id)
        except ComputerCommand.DoesNotExist:
            return Response(
                {"detail": "Command not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if command.status != CommandStatus.PENDING:
            return Response(
                {"detail": f"Cannot cancel command with status '{command.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        command.status = CommandStatus.CANCELLED
        command.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Command cancelled."})


@extend_schema(tags=["Computers - Commands"])
class PendingCommandsAPIView(APIView):
    """
    PC client: fetch pending commands for this computer.
    The client polls this endpoint every ~30 seconds.
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "pc_register"

    def get(self, request):
        from apps.computers.models import Computer

        hardware_id = request.query_params.get("hardware_id")
        computer_id = request.query_params.get("computer_id")

        qs = ComputerCommand.objects.filter(
            status=CommandStatus.PENDING
        ).select_related("game")

        if hardware_id:
            qs = qs.filter(computer__hardware_id=hardware_id)
        elif computer_id:
            qs = qs.filter(computer_id=computer_id)
        else:
            return Response(
                {"detail": "hardware_id or computer_id required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ComputerCommandSerializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(tags=["Computers - Commands"])
class CommandStatusUpdateAPIView(APIView):
    """
    PC client: update the status of a command being executed.
    """

    permission_classes = [permissions.AllowAny]
    throttle_scope = "pc_register"

    def patch(self, request, command_id):
        try:
            command = ComputerCommand.objects.get(pk=command_id)
        except ComputerCommand.DoesNotExist:
            return Response(
                {"detail": "Command not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ComputerCommandStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        command.status = data["status"]
        command.error_message = data.get("error_message", "")
        command.save(update_fields=["status", "error_message", "updated_at"])

        # When a game install/update COMPLETES, record the now-installed version on
        # the PC so the auto-update detector stops flagging it as outdated.
        if data["status"] == CommandStatus.COMPLETED and command.game_id and command.command_type in ("install", "reinstall", "update", "update_app"):
            try:
                from apps.computers.models.computer_game import ComputerGame
                ver = (command.payload or {}).get("version") or getattr(command.game, "version", "") or ""
                ComputerGame.objects.update_or_create(
                    computer_id=command.computer_id, game_id=command.game_id,
                    defaults={"is_installed": command.command_type != "uninstall",
                              "installed_version": ver},
                )
            except Exception:
                pass

        return Response(ComputerCommandSerializer(command).data)

@extend_schema(tags=["Admin - Software Management"])
class BulkCommandAPIView(APIView):
    """
    Admin: Send a command to multiple computers at once.
    
    Expected JSON:
    {
        "computer_ids": [1, 2, 3] or "all",
        "command_type": "install" | "update" | "uninstall",
        "game_id": 1 (optional),
        "payload": { ... }
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        computer_ids = request.data.get("computer_ids")
        command_type = request.data.get("command_type")
        game_id = request.data.get("game_id")
        payload = request.data.get("payload", {})

        if not command_type:
            return Response({"error": "command_type is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Tenant scope: a broadcast must stay inside the operator's club, never
        # touch other clubs' machines.
        club_id = getattr(request, "current_club_id", None) or request.data.get("club")

        # Fleet management is allowed to the club owner / manager / platform admin —
        # not only a platform admin (the owner must control their own machines).
        u = request.user
        is_platform_admin = getattr(u, "is_admin", False) or getattr(u, "user_type", "") == "admin"
        if not is_platform_admin:
            if not club_id:
                return Response({"error": "club required"}, status=status.HTTP_400_BAD_REQUEST)
            from apps.clubs.models import Club, ClubMembership
            allowed = Club.objects.filter(id=club_id, owner=u).exists() or ClubMembership.objects.filter(
                user=u, club_id=club_id, is_active=True, role__in=["owner", "manager"]
            ).exists()
            if not allowed:
                return Response({"error": "Нет прав на управление ПК этого клуба"}, status=status.HTTP_403_FORBIDDEN)

        base_qs = Computer.objects.filter(is_active=True)
        if club_id:
            base_qs = base_qs.filter(club_id=club_id)

        if computer_ids == "all":
            computers = base_qs
        elif isinstance(computer_ids, list):
            # Still constrained to the club so you can't enqueue onto foreign PCs.
            computers = base_qs.filter(id__in=computer_ids)
        else:
            return Response({"error": "computer_ids must be a list or 'all'"}, status=status.HTTP_400_BAD_REQUEST)

        game = None
        if game_id:
            game = Game.objects.filter(pk=game_id).first()

        # Auto-enrich the payload from the game so the shell knows HOW to install:
        # Steam titles → steam://install/<app_id>; others → download installer_url.
        if game:
            payload = {
                **payload,
                "game_name": game.name,
                "platform": getattr(game, "platform", "") or "",
                "app_id": getattr(game, "app_id", "") or "",
                "version": getattr(game, "version", "") or "",
                # For non-Steam, installer_url should point at the club LAN server.
                "installer_url": payload.get("installer_url") or getattr(game, "executable_path", "") or "",
            }

        commands_created = 0
        for pc in computers:
            ComputerCommand.objects.create(
                computer=pc,
                game=game,
                command_type=command_type,
                status=CommandStatus.PENDING,
                payload=payload,
                created_by=request.user
            )
            commands_created += 1

        return Response({
            "detail": f"Successfully created {commands_created} commands.",
            "commands_created": commands_created
        }, status=status.HTTP_201_CREATED)
