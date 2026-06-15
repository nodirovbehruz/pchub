from typing import Any, Dict, List

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.computers.models import Computer, ComputerStatus
from apps.computers.repositories.implementation.computer import ComputerRepository
from apps.computers.repositories.interface.computer import IComputerRepository
from apps.computers.services.interface.computer import IComputerService
from apps.games.models import GameSession, SessionStatus


class ComputerService(IComputerService):
    """Service for Computer management"""

    def __init__(self, repository: IComputerRepository = None):
        self.repository = repository or ComputerRepository()

    @transaction.atomic
    def register_computer(self, data: Dict[str, Any]) -> Computer:
        """
        Register a new computer from C# app

        If hardware_id is provided and computer exists, return existing computer
        and update its information. Otherwise, create new computer.
        """
        # Validate required fields
        if "name" not in data:
            raise ValidationError({"name": "Computer name is required"})

        # Check if computer with this hardware_id already exists (if hardware_id provided)
        hardware_id = data.get("hardware_id")
        if hardware_id:
            existing_computer = Computer.objects.filter(hardware_id=hardware_id).first()
        else:
            existing_computer = None

        if existing_computer:
            # Update existing computer's information
            allowed_fields = [
                "name",
                "description",
                "cpu_model",
                "cpu_cores",
                "cpu_threads",
                "ram_total_gb",
                "gpu_model",
                "storage_total_gb",
                "os_name",
                "os_version",
                "ip_address",
                "mac_address",
            ]
            update_data = {k: v for k, v in data.items() if k in allowed_fields}

            # Update status to ONLINE
            from django.utils import timezone

            from apps.computers.models import ComputerStatus

            update_data["status"] = ComputerStatus.ONLINE
            update_data["last_seen"] = timezone.now()

            # BUGFIX: re-registration ignored club_token, so a re-imaged PC stayed in
            # its old club. If a valid club_token resolved to a DIFFERENT club, move it.
            new_club = data.get("club_id") or data.get("club")
            if hasattr(new_club, "id"):
                new_club = new_club.id
            if new_club and new_club != existing_computer.club_id:
                update_data["club_id"] = new_club

            return self.repository.update(existing_computer, **update_data)

        # Enforce the club's subscription PC limit (max_pcs) for NEW computers only
        # (re-registration of an existing PC returned above and is always allowed).
        club_id = data.get("club_id") or data.get("club")
        if hasattr(club_id, "id"):
            club_id = club_id.id
        # BUGFIX: a NEW PC with no club becomes invisible to every admin (all lists
        # filter by club_id) and bypasses the PC limit. Require a club for new PCs.
        if not club_id:
            raise ValidationError({"club": "Не указан клуб (нужен корректный club_token)"})
        if club_id:
            from apps.clubs.models import Club
            from apps.clubs.services import billing as billing_service
            # Lock the club row so concurrent registrations can't both pass the
            # count check and overshoot max_pcs (held until this atomic method commits).
            Club.objects.select_for_update().filter(id=club_id).first()
            if not billing_service.can_add_pc(club_id):
                u = billing_service.pc_usage(club_id)
                raise ValidationError({
                    "limit": f"Достигнут лимит ПК по тарифу: {u['used']}/{u['limit']}. "
                             f"Обновите тариф, чтобы добавить больше компьютеров."
                })

        # Generate slug if not provided
        if "slug" not in data:
            data["slug"] = slugify(data["name"])

        # Check if slug already exists
        if self.repository.get_by_slug(data["slug"]):
            # Append timestamp to make it unique
            from django.utils import timezone

            data["slug"] = f"{data['slug']}-{int(timezone.now().timestamp())}"

        # BUGFIX: Computer.name is globally unique, but clubs reuse generic machine
        # names ("PC-01") — a second club's identical name raised a raw IntegrityError
        # in the shell. Auto-suffix the name on collision, like the slug.
        if Computer.objects.filter(name=data["name"]).exists():
            from django.utils import timezone
            data["name"] = f"{data['name']}-{int(timezone.now().timestamp())}"

        # Generate a temporary hardware_id if not provided (for backwards compatibility)
        if not hardware_id:
            import uuid

            data["hardware_id"] = f"temp-{uuid.uuid4().hex[:32]}"

        # Set initial status to ONLINE
        from django.utils import timezone

        from apps.computers.models import ComputerStatus

        data["status"] = ComputerStatus.ONLINE
        data["last_seen"] = timezone.now()

        # Create computer
        computer = self.repository.create(**data)

        # Auto-assign next PC number if not set — PER CLUB (was global, so the first
        # PC of a new club could be "#84" and numbers leaked across tenants).
        if not computer.pc_number:
            from django.db.models import Max
            base_qs = (Computer.objects.filter(club_id=computer.club_id)
                       if computer.club_id else Computer.objects.all())
            max_num = base_qs.aggregate(Max('pc_number'))['pc_number__max'] or 0
            computer.pc_number = max_num + 1
            computer.save(update_fields=['pc_number'])

        return computer

    def update_computer_specs(self, computer_id: int, data: Dict[str, Any]) -> Computer:
        """Update computer hardware specifications"""
        # Get computer
        computer = self.repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        # Update specs
        allowed_fields = [
            "cpu_model",
            "cpu_cores",
            "cpu_threads",
            "ram_total_gb",
            "gpu_model",
            "storage_total_gb",
            "os_name",
            "os_version",
            "ip_address",
            "mac_address",
        ]

        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        computer = self.repository.update(computer, **update_data)

        return computer

    def get_computer_overview(self, computer_id: int) -> Dict[str, Any]:
        """Get complete computer overview with stats"""
        # Get computer
        computer = self.repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        return {
            "computer": computer,
            "installed_games_count": computer.installed_games_count,
            "total_gaming_hours": float(computer.total_gaming_hours),
            "latest_metrics": computer.latest_metrics,
            "status": computer.status,
            "last_seen": computer.last_seen,
        }

    def heartbeat(self, computer_id: int) -> Dict[str, Any]:
        """Update computer heartbeat - set status to ONLINE and update last_seen"""
        computer = self.repository.get_by_id(computer_id)
        if not computer:
            raise ValidationError({"computer_id": "Computer not found"})

        computer.last_seen = timezone.now()
        # Don't stomp an operator-set MAINTENANCE/DISABLED state — only mark ONLINE
        # from offline/online. (Heartbeat refreshes last_seen regardless.)
        fields = ["last_seen"]
        if computer.status not in (ComputerStatus.MAINTENANCE, ComputerStatus.DISABLED):
            computer.status = ComputerStatus.ONLINE
            fields.append("status")
        computer.save(update_fields=fields)

        return {
            "success": True,
            "timestamp": computer.last_seen,
            "status": computer.status,
        }

    def get_all_computers_status(self) -> List[Dict[str, Any]]:
        """Get all computers with their current status and active sessions"""

        computers = Computer.objects.all().order_by("-last_seen")
        result = []

        for computer in computers:
            # Find active session on this computer
            active_session = (
                GameSession.objects.filter(
                    computer=computer, session_status=SessionStatus.ACTIVE
                )
                .select_related("account", "game")
                .first()
            )

            computer_data = {
                "computer_id": computer.id,
                "machine_name": computer.name,
                "status": computer.status,
                "last_seen": computer.last_seen,
                "owner": computer.owner.username if computer.owner else None,
            }

            if active_session:
                # Calculate session duration
                duration = timezone.now() - active_session.current_session_start
                duration_minutes = int(duration.total_seconds() / 60)

                computer_data.update(
                    {
                        "current_user": active_session.account.username,
                        "current_game": active_session.game.name,
                        "current_game_id": active_session.game.id,
                        "session_duration": (
                            f"{duration_minutes} minutes"
                            if duration_minutes < 60
                            else f"{duration_minutes // 60}h {duration_minutes % 60}min"
                        ),
                        "session_duration_minutes": duration_minutes,
                    }
                )
            else:
                computer_data.update(
                    {
                        "current_user": None,
                        "current_game": None,
                        "current_game_id": None,
                        "session_duration": None,
                        "session_duration_minutes": 0,
                    }
                )

            result.append(computer_data)

        return result
