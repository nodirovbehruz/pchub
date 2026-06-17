"""Batch 9 — regressions for tenant/authz fixes applied in earlier commits."""
from decimal import Decimal

import pytest


# ── Task.club is read-only on update (no cross-club move via PATCH) ──────────
@pytest.mark.django_db
def test_task_club_is_read_only_on_update(api, make_club):
    from apps.content.models import Task
    club_a = make_club()
    club_b = make_club()
    t = Task.objects.create(club=club_a, title="T")

    api.force_authenticate(user=club_a.owner)
    api.patch(f"/api/v1/content/tasks/{t.id}/?club={club_a.id}",
              {"club": club_b.id, "title": "T2"}, format="json")
    t.refresh_from_db()
    assert t.club_id == club_a.id  # club must not change


# ── Admin command list is scoped to clubs the caller manages ─────────────────
@pytest.mark.django_db
def test_admin_command_list_scoped(api, make_club, make_user, make_membership):
    from apps.computers.models import Computer, ComputerCommand
    from apps.computers.models.command import CommandType
    club_a = make_club()
    club_b = make_club()
    pc_a = Computer.objects.create(name="PC-cmd-a", club=club_a)
    cmd = ComputerCommand.objects.create(computer=pc_a, command_type=CommandType.LOCK)

    user = make_user()
    make_membership(user, club_b, role="manager")  # only in club_b
    api.force_authenticate(user=user)

    resp = api.get("/api/v1/computers/admin/commands/")
    assert resp.status_code == 200
    data = resp.json()
    ids = [c.get("id") for c in data] if isinstance(data, list) else [
        c.get("id") for c in data.get("results", [])]
    assert cmd.id not in ids  # must not see club_a's command


# ── Re-registration cannot move a PC into a different club ───────────────────
@pytest.mark.django_db
def test_register_cannot_hijack_pc_into_another_club(make_club):
    from apps.computers.models import Computer
    from apps.computers.services.implementation.computer import ComputerService
    from rest_framework.exceptions import ValidationError
    club_a = make_club()
    club_b = make_club()
    Computer.objects.create(name="PC-hijack", hardware_id="HWHIJACK", club=club_a)

    svc = ComputerService()
    with pytest.raises(ValidationError):
        svc.register_computer({"name": "PC-hijack", "hardware_id": "HWHIJACK", "club_id": club_b.id})
    # PC stayed in club_a
    assert Computer.objects.get(hardware_id="HWHIJACK").club_id == club_a.id


# ── Promocode targeting (specific_clients) is enforced ───────────────────────
@pytest.mark.django_db
def test_promocode_specific_clients_enforced(api, make_club, make_user, make_profile):
    from apps.loyalty.models import Promocode
    club = make_club()
    target = make_user()
    other = make_user()
    make_profile(target, club)
    make_profile(other, club)
    p = Promocode.objects.create(club=club, code="VIPONLY", reward_type="deposit_topup",
                                 value=Decimal("50"), is_active=True)
    p.specific_clients.add(target)

    api.force_authenticate(user=club.owner)
    bad = api.post(f"/api/v1/loyalty/promocodes/apply/?club={club.id}",
                   {"code": "VIPONLY", "client_id": str(other.id)}, format="json")
    assert bad.status_code == 403  # not a targeted client

    ok = api.post(f"/api/v1/loyalty/promocodes/apply/?club={club.id}",
                  {"code": "VIPONLY", "client_id": str(target.id)}, format="json")
    assert ok.status_code == 200, ok.content
