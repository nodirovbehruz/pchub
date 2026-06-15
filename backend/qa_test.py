"""
QA Test Suite - PCHub PRO SENET Features
"""
import os, sys, io, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append("testserver")


import json
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.computers.models import Computer
from apps.computers.models.command import ComputerCommand
from apps.billing.models import Abonement, Shift, PurchasedAbonement

User = get_user_model()
PASS = "[OK]"
FAIL = "[FAIL]"
results = []

def log(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((name, passed))
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))

print("\n" + "="*60)
print("  QA TEST SUITE — PCHub PRO (SENET Features)")
print("="*60)

# ── Setup ────────────────────────────────────────────────────
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    print(f"{FAIL} CRITICAL: No superuser found! Cannot test.")
    sys.exit(1)

factory = RequestFactory()

# ── Test 1: Database State ───────────────────────────────────
print("\n[1] DATABASE STATE")
pc_count = Computer.objects.count()
log("Computers exist", pc_count > 0, f"count={pc_count}")

ab_count = Abonement.objects.count()
log("Abonements exist", ab_count > 0, f"count={ab_count}")

abs_active = Abonement.objects.filter(is_active=True).count()
log("Active abonements", abs_active > 0, f"active={abs_active}")

# ── Test 2: Shift Logic ─────────────────────────────────────
print("\n[2] SHIFT LOGIC")
# Ensure no active shift
active = Shift.get_active_shift()
if active:
    active.close_shift()
log("Shift is closed initially", Shift.get_active_shift() is None)

# Open shift
new_shift = Shift.objects.create(admin=admin_user)
log("Shift opened successfully", Shift.get_active_shift() is not None)
log("Shift admin matches", Shift.get_active_shift().admin == admin_user)

# Close shift
new_shift.close_shift()
log("Shift closed successfully", Shift.get_active_shift() is None)

# ── Test 3: Abonement API ───────────────────────────────────
print("\n[3] ABONEMENT API (via Django Test Client)")
from django.test import Client
client = Client()
client.force_login(admin_user)

# Test abonements-api endpoint
response = client.get("/admin/computers/computer/club-map/abonements-api/")
log("Abonements API responds", response.status_code == 200, f"status={response.status_code}")

if response.status_code == 200:
    data = json.loads(response.content)
    log("API returns abonements list", "abonements" in data)
    log("Correct abonement count", len(data.get("abonements", [])) == abs_active, 
        f"returned={len(data.get('abonements', []))}, expected={abs_active}")
    if data.get("abonements"):
        sample = data["abonements"][0]
        log("Abonement has 'name'", "name" in sample)
        log("Abonement has 'price'", "price" in sample)
        log("Abonement has 'duration'", "duration" in sample)

# ── Test 4: Status API ──────────────────────────────────────
print("\n[4] STATUS API")
response = client.get("/admin/computers/computer/club-map/status-api/")
log("Status API responds", response.status_code == 200, f"status={response.status_code}")

if response.status_code == 200:
    data = json.loads(response.content)
    log("Contains 'computers' key", "computers" in data)
    log("Contains 'shift' key", "shift" in data)
    log("Shift reports inactive", data["shift"]["is_active"] == False)
    log("Correct PC count in API", len(data.get("computers", [])) == pc_count, 
        f"returned={len(data.get('computers', []))}, expected={pc_count}")

# ── Test 5: Bulk Command API ────────────────────────────────
print("\n[5] BULK COMMAND API")
test_pcs = list(Computer.objects.values_list("id", flat=True)[:3])
cmd_count_before = ComputerCommand.objects.count()

response = client.post(
    "/admin/computers/computer/club-map/bulk-command/",
    data=json.dumps({"ids": test_pcs, "command": "REBOOT"}),
    content_type="application/json"
)
log("Bulk command API responds", response.status_code == 200, f"status={response.status_code}")

if response.status_code == 200:
    data = json.loads(response.content)
    log("Bulk command success", data.get("success") == True)
    cmd_count_after = ComputerCommand.objects.count()
    log("Commands created for each PC", cmd_count_after - cmd_count_before == len(test_pcs),
        f"created={cmd_count_after - cmd_count_before}, expected={len(test_pcs)}")

# ── Test 6: Purchase Abonement (without active user) ────────
print("\n[6] PURCHASE ABONEMENT (Edge Case: No User on PC)")
# Open shift first
shift = Shift.objects.create(admin=admin_user)

first_pc = Computer.objects.first()
first_ab = Abonement.objects.first()

response = client.post(
    "/admin/computers/computer/club-map/purchase-abonement/",
    data=json.dumps({"pc_id": first_pc.id, "ab_id": first_ab.id}),
    content_type="application/json"
)
log("Purchase API responds", response.status_code == 200, f"status={response.status_code}")
if response.status_code == 200:
    data = json.loads(response.content)
    log("Purchase blocked (no user on PC)", data.get("success") == False,
        f"error={data.get('error', 'none')[:60]}")

shift.close_shift()

# ── Test 7: Club Map Page ───────────────────────────────────
print("\n[7] CLUB MAP PAGE")
response = client.get("/admin/computers/computer/club-map/")
log("Club map page loads", response.status_code == 200, f"status={response.status_code}")

if response.status_code == 200:
    content = response.content.decode("utf-8")
    log("Contains PCHub PRO title", "PCHub" in content)
    log("Contains Управление button", "Управление" in content or "manage" in content.lower())
    log("Contains font-awesome", "font-awesome" in content)
    log("Contains status-api endpoint", "status-api" in content)
    log("Contains abonements-api endpoint", "abonements-api" in content)
    log("Contains bulk-command endpoint", "bulk-command" in content or "bulkCmd" in content)
    log("Contains purchase-abonement endpoint", "purchase-abonement" in content)

# ── Test 8: Admin Panel Registration ────────────────────────
print("\n[8] ADMIN PANEL REGISTRATION")
response = client.get("/admin/billing/abonement/")
log("Abonement admin page loads", response.status_code == 200, f"status={response.status_code}")

response = client.get("/admin/billing/purchasedabonement/")
log("PurchasedAbonement admin page loads", response.status_code == 200, f"status={response.status_code}")

# ── SUMMARY ─────────────────────────────────────────────────
print("\n" + "="*60)
total = len(results)
passed = sum(1 for _, p in results if p)
failed = total - passed
print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print(f"  {PASS} ALL TESTS PASSED!")
else:
    print(f"  {FAIL} SOME TESTS FAILED:")
    for name, p in results:
        if not p:
            print(f"    {FAIL} {name}")
print("="*60 + "\n")

# Cleanup test commands
ComputerCommand.objects.filter(command_type="REBOOT", created_by=admin_user).delete()
