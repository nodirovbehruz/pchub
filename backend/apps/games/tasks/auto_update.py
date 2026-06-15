"""Auto-update orchestration for fleet games (Celery Beat, every few minutes).

Compares each PC's installed game version against the game's target version and
enqueues an `update` command for the lagging PCs — but only when the PC is online
and NOT in an active session (so updates never interrupt a player). Files are
delivered by the club's local source (Steam/LanCache or a LAN share); the backend
only orchestrates.
"""

from celery import shared_task


@shared_task(name="apps.games.tasks.sync_game_versions")
def sync_game_versions():
    from django.db.models import F
    from apps.computers.models import ComputerCommand
    from apps.computers.models.command import CommandStatus, CommandType
    from apps.computers.models.computer_game import ComputerGame

    result = {"queued": 0, "skipped_busy": 0, "outdated": 0}

    outdated = (
        ComputerGame.objects.filter(is_installed=True)
        .exclude(installed_version=F("game__version"))
        .select_related("computer", "game")
    )
    for cg in outdated:
        game = cg.game
        if not game or not (game.version or "").strip():
            continue
        if (cg.installed_version or "") == (game.version or ""):
            continue
        result["outdated"] += 1
        pc = cg.computer

        if (pc.status or "").lower() != "online":
            result["skipped_busy"] += 1
            continue
        if _pc_in_session(pc):
            result["skipped_busy"] += 1
            continue

        if ComputerCommand.objects.filter(
            computer=pc, game=game, command_type=CommandType.UPDATE,
            status=CommandStatus.PENDING,
        ).exists():
            continue

        ComputerCommand.objects.create(
            computer=pc, game=game, command_type=CommandType.UPDATE,
            status=CommandStatus.PENDING,
            payload={
                "game_name": game.name,
                "platform": getattr(game, "platform", "") or "",
                "app_id": getattr(game, "app_id", "") or "",
                "version": game.version,
                "installer_url": getattr(game, "executable_path", "") or "",
            },
        )
        result["queued"] += 1

    return result


def _pc_in_session(pc) -> bool:
    """True if someone is currently playing on this PC (guest postpaid or a client
    with an active session) — we must not interrupt them with an update."""
    try:
        from apps.accounts.models import CustomUser
        from apps.clubs.models import UserClubProfile
        guest = CustomUser.objects.filter(username=f"guest-pc-{pc.id}").first()
        if guest and UserClubProfile.objects.filter(
            user=guest, club_id=pc.club_id, session_mode="postpaid", is_active=True
        ).exists():
            return True
        if pc.hardware_id and CustomUser.objects.filter(
            active_hardware_id=pc.hardware_id, is_active_session=True
        ).exists():
            return True
    except Exception:
        return False
    return False
