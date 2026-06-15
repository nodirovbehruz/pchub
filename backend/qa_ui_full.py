"""
PCHUB PRO — Full UI/UX Automated Test Suite
Checks every page for: HTTP 200, sidebar presence, key UI elements
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append("testserver")

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
WARN = "\033[93m WARN\033[0m"
INFO = "\033[94m INFO\033[0m"

results = []

def check(name, condition, detail=""):
    icon = PASS if condition else FAIL
    print(f"  [{icon}] {name}" + (f" — {detail}" if detail else ""))
    results.append((name, condition))
    return condition

def section(title):
    print(f"\n\033[1m{'='*55}\033[0m")
    print(f"\033[1m  {title}\033[0m")
    print(f"\033[1m{'='*55}\033[0m")


print("\n\033[1m  PCHUB PRO — FULL UI/UX AUTOMATED AUDIT\033[0m")

# ── Setup ──────────────────────────────────────────────────────────────────────
client = Client()
username = "pchub_qa_tester"
password = "qatest12345"

try:
    u = User.objects.get(username=username)
except User.DoesNotExist:
    u = User.objects.create_superuser(username=username, email="qa@pchub.test", password=password)

login_ok = client.login(username=username, password=password)

# ── Test 1: Login page ─────────────────────────────────────────────────────────
section("1. LOGIN PAGE")
client_anon = Client()
r = client_anon.get("/admin/login/")
check("Login page loads (HTTP 200)", r.status_code == 200)
check("Login form present", b'<form' in r.content)
check("SENET sidebar NOT shown on login", b'id="senet-sidebar"' not in r.content,
      "Sidebar absent for anonymous users")

# ── Test 2: Admin index ────────────────────────────────────────────────────────
section("2. ADMIN INDEX (Dashboard)")
r = client.get("/admin/")
check("Admin index loads (HTTP 200)", r.status_code == 200)
content = r.content.decode("utf-8", errors="replace")
check("SENET Sidebar present", 'id="senet-sidebar"' in content)
check("Brand logo shown (PCHUB PRO)", 'PCHUB PRO' in content)
check("Navigation links present", 'senet-nav-item' in content)
check("Kasssa link present", '/admin/billing/shift/dashboard/' in content)
check("POS link present", '/admin/shops/product/pos/' in content)
check("Club map link present", '/admin/computers/computer/club-map/' in content)
check("User avatar (initials) shown", 'senet-avatar' in content)
check("Logout button present", '/admin/logout/' in content)
check("Hotwire Turbo loaded", 'hotwired/turbo' in content)
check("Inter font loaded", 'fonts.googleapis.com' in content)
check("FontAwesome loaded", 'font-awesome' in content)
check("Sidebar section labels present", 'senet-nav-label' in content)
check("Turbo:load JS event hooked", 'turbo:load' in content)
check("Jazzmin main-header hidden", '.main-header' in content and 'display: none' in content)

# ── Test 3: Club map ───────────────────────────────────────────────────────────
section("3. CLUB MAP")
r = client.get("/admin/computers/computer/club-map/")
check("Club map loads (HTTP 200)", r.status_code == 200)
content = r.content.decode("utf-8", errors="replace")
check("Sidebar present", 'id="senet-sidebar"' in content)
check("Map container present", 'club-map' in content or 'computer-card' in content or 'computers' in content.lower())

# ── Test 4: Cash Register ──────────────────────────────────────────────────────
section("4. CASH REGISTER (X/Z Reports)")
r = client.get("/admin/billing/shift/dashboard/")
check("Cash Register loads (HTTP 200)", r.status_code == 200)
content = r.content.decode("utf-8", errors="replace")
check("Sidebar present", 'id="senet-sidebar"' in content)
check("Page title shown", 'Управление Кассой' in content)
check("X-Report block present", 'X-Отчет' in content)
check("Z-Report block present", 'Z-Отчет' in content)
check("Status badge present", 'status-badge' in content)
check("Open shift button available", 'btn-open-shift' in content or 'ОТКРЫТЬ СМЕНУ' in content)
check("Recent shifts table present", 'История Смен' in content)

# ── Test 5: Shop POS ───────────────────────────────────────────────────────────
section("5. SHOP POS TERMINAL")
r = client.get("/admin/shops/product/pos/")
check("Shop POS loads (HTTP 200)", r.status_code == 200)
content = r.content.decode("utf-8", errors="replace")
check("Sidebar present", 'id="senet-sidebar"' in content)
check("Product grid present", 'products-grid' in content)
check("Cart container present", 'cart-items' in content)
check("Pay button present", 'К ОПЛАТЕ' in content)
check("Category filter tabs present", 'category-tab' in content)
check("Cart JS logic present", 'function addToCart' in content)

# ── Test 6: Users (CRM) ────────────────────────────────────────────────────────
section("6. USERS (CRM)")
r = client.get("/admin/accounts/customuser/")
check("Users page loads (HTTP 200)", r.status_code == 200)
content = r.content.decode("utf-8", errors="replace")
check("Sidebar present", 'id="senet-sidebar"' in content)

# ── Test 7: CSS Variables Defined ─────────────────────────────────────────────
section("7. DESIGN SYSTEM — CSS Variables")
r = client.get("/admin/")
content = r.content.decode("utf-8", errors="replace")
check("--senet-bg-dark defined", '--senet-bg-dark' in content)
check("--senet-accent defined", '--senet-accent' in content)
check("--senet-border defined", '--senet-border' in content)
check("--success defined", '--success' in content)
check("--danger defined", '--danger' in content)
check("Scrollbar custom style", '::-webkit-scrollbar' in content)
check("Dark card styles present", '.card' in content)
check("Table dark-mode styles", '.table' in content)

# ── Summary ────────────────────────────────────────────────────────────────────
section("SUMMARY")
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total = len(results)
pct = round(passed / total * 100)
print(f"\n  Total:  {total} checks")
print(f"  Passed: \033[92m{passed}\033[0m")
print(f"  Failed: \033[91m{failed}\033[0m")
print(f"  Score:  {pct}%\n")

if failed:
    print("  Failed checks:")
    for name, ok in results:
        if not ok:
            print(f"    - {name}")

sys.exit(0 if failed == 0 else 1)
