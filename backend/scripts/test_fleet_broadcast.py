"""
Fleet broadcast test — proves "an action on the admin reaches EVERY PC in the club"
without needing many physical machines.

It simulates N virtual PCs (distinct hardware_ids in one club), sends ONE bulk
command from the operator, then checks each PC's pending-commands feed to confirm
they ALL received it.

Run (backend must be up on :8000):
    DJANGO_SETTINGS_MODULE=settings python scripts/test_fleet_broadcast.py
Optional: pass club id as arg 1 (default 4) and PC count as arg 2 (default 3).
"""
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# Make the project root importable so `settings` resolves when run from scripts/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

import django  # noqa: E402
django.setup()

import urllib.request  # noqa: E402
import urllib.error  # noqa: E402
import json  # noqa: E402
from apps.clubs.models import Club  # noqa: E402
from apps.computers.models import Computer  # noqa: E402
from apps.computers.models.command import ComputerCommand  # noqa: E402
from rest_framework_simplejwt.tokens import RefreshToken  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
CLUB_ID = int(sys.argv[1]) if len(sys.argv) > 1 else 4
N = int(sys.argv[2]) if len(sys.argv) > 2 else 3


def api(path, method="GET", token=None, body=None, club=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if club:
        req.add_header("X-Club-Id", str(club))
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, (e.read()[:200]).decode(errors="ignore")


def main():
    club = Club.objects.get(id=CLUB_ID)
    print(f"== Клуб {CLUB_ID}: {club.name} ==")

    # 1) ensure N virtual PCs in this club
    hw_ids = []
    for i in range(1, N + 1):
        hw = f"test-fleet-{i}"
        pc, created = Computer.objects.get_or_create(
            hardware_id=hw,
            defaults={"name": f"FLEET-{i}", "club_id": CLUB_ID, "is_active": True, "slug": f"fleet-{CLUB_ID}-{i}"},
        )
        if pc.club_id != CLUB_ID or not pc.is_active:
            pc.club_id = CLUB_ID
            pc.is_active = True
            pc.save()
        hw_ids.append((pc.id, hw))
        print(f"   ПК #{pc.id}  hw={hw}  ({'создан' if created else 'есть'})")

    # clear old pending so the test is clean
    ComputerCommand.objects.filter(computer__hardware_id__in=[h for _, h in hw_ids]).delete()

    # 2) operator broadcasts ONE command to the whole club
    owner_token = str(RefreshToken.for_user(club.owner).access_token)
    print("\n== BROADCAST: установить условную команду на ВСЕ ПК клуба ==")
    st, resp = api(
        "/computers/admin/commands/bulk/", method="POST", token=owner_token, club=CLUB_ID,
        body={"computer_ids": "all", "command_type": "update", "payload": {"note": "fleet test"}},
    )
    print(f"   ответ bulk: HTTP {st} -> {resp}")

    # 3) verify EACH PC received it via its own pending feed (what the shell polls)
    print("\n== Проверка доставки на каждый ПК (его лента pending) ==")
    ok = 0
    for pc_id, hw in hw_ids:
        st, resp = api(f"/computers/commands/pending/?hardware_id={hw}")
        got = isinstance(resp, list) and len(resp) > 0
        print(f"   ПК {hw}: HTTP {st}, команд в очереди = {len(resp) if isinstance(resp, list) else '?'}  {'✓ ДОЛЕТЕЛО' if got else '✗ НЕТ'}")
        if got:
            ok += 1

    print(f"\n== ИТОГ: {ok}/{len(hw_ids)} ПК получили broadcast ==")
    print("Так это и работает на реальном парке: оператор жмёт раз — команда у всех в очереди,")
    print("каждый шелл забирает её поллером (30с) или мгновенно по WebSocket и выполняет.")


if __name__ == "__main__":
    main()
