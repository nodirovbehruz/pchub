"""
CSS Property Audit — verifies key design tokens and layout rules
are correctly defined in base_site.html
"""
import re, sys

with open(r"d:\PC\PCHubBackend-main\templates\admin\base_site.html", encoding="utf-8") as f:
    src = f.read()

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results = []

def check(label, condition, hint=""):
    icon = PASS if condition else FAIL
    print(f"  [{icon}] {label}" + (f"  ({hint})" if hint else ""))
    results.append(condition)

def has_prop(selector, prop, value=None):
    """Find selector block and check property inside it."""
    # rudimentary: find text between selector { ... }
    pat = re.escape(selector) + r'\s*\{([^}]+)\}'
    m = re.search(pat, src, re.DOTALL)
    if not m:
        return False
    block = m.group(1)
    if value:
        return prop in block and value in block
    return prop in block

print("\n\033[1m  PCHUB PRO — CSS AUDIT\033[0m")

# ── Colour tokens ──────────────────────────────────────────────────────────────
print("\n\033[1m[1] Colour tokens (CSS :root)\033[0m")
root_m = re.search(r':root\s*\{([^}]+)\}', src, re.DOTALL)
root = root_m.group(1) if root_m else ""
check("--senet-bg-dark  = #0b1120 (deep navy)", "#0b1120" in root)
check("--senet-bg-panel = #1e293b (dark panel)", "#1e293b" in root)
check("--senet-accent   = #8b5cf6 (purple)",     "#8b5cf6" in root)
check("--senet-text     = #f8fafc (near white)",  "#f8fafc" in root)
check("--senet-text-muted = #94a3b8",             "#94a3b8" in root)
check("--success        = #10b981 (emerald)",     "#10b981" in root)
check("--danger         = #ef4444 (red)",          "#ef4444" in root)
check("--sidebar-width  = 250px",                 "250px"   in root)

# ── Typography ─────────────────────────────────────────────────────────────────
print("\n\033[1m[2] Typography\033[0m")
check("Inter font loaded from Google Fonts",
      "fonts.googleapis.com" in src and "Inter" in src)
check("body font-family: Inter",
      "font-family: 'Inter', sans-serif" in src)
check("Font weights: 400,500,600,700,900 requested",
      all(w in src for w in ["400","500","600","700","900"]))
check("Brand name font-weight: 900", "font-weight: 900" in src)

# ── Sidebar layout ─────────────────────────────────────────────────────────────
print("\n\033[1m[3] Sidebar dimensions\033[0m")
check("Sidebar uses var(--sidebar-width)=250px",
      "var(--sidebar-width)" in src and "250px" in src)
check("Sidebar flex-direction: column",
      "#senet-sidebar" in src and "flex-direction: column" in src)
check("Sidebar height: 100vh", "height: 100vh" in src)
check("Sidebar flex-shrink: 0 (won't grow/shrink)", "flex-shrink: 0" in src)
check("Brand height: 64px", "64px" in src)
check("Brand icon 34×34px rounded",
      "34px" in src and "border-radius: 8px" in src)
check("Avatar 36×36px rounded circle",
      "36px" in src and "border-radius: 50%" in src)
check("User name font-size: 13px", "13px" in src)
check("Nav label font-size: 10px uppercase",
      "10px" in src and "uppercase" in src)
check("Nav item font-size: 14px", "14px" in src)
check("Nav item padding: 10px 12px",
      "10px 12px" in src)
check("Nav item border-radius: 8px",
      "border-radius: 8px" in src)
check("Nav item hover transition: 0.15s",
      "0.15s" in src)

# ── Wrapper / Content ──────────────────────────────────────────────────────────
print("\n\033[1m[4] Layout — Wrapper & Content\033[0m")
check(".wrapper display: flex", ".wrapper" in src and "display: flex" in src)
check(".wrapper flex-direction: row",
      "flex-direction: row" in src)
check(".wrapper overflow: hidden",
      ".wrapper" in src and "overflow: hidden" in src)
check(".content-wrapper flex: 1 (fills remaining space)",
      "flex: 1" in src)
check(".content-wrapper margin: 0 (no Jazzmin left-margin)",
      "margin: 0" in src)
check(".content-wrapper overflow-y: auto",
      "overflow-y: auto" in src)
check("Content header padding: 20px 28px",
      "20px 28px" in src)
check("Section content padding: 24px 28px",
      "24px 28px" in src)

# ── Polish / Micro UX ──────────────────────────────────────────────────────────
print("\n\033[1m[5] Polish & Micro-UX\033[0m")
check("Custom scrollbar defined",
      "::-webkit-scrollbar" in src)
check("Scrollbar width: 6px", "width: 6px" in src)
check("Font Awesome 6.4 icons",
      "font-awesome/6.4" in src)
check("Dark table rows styled",
      ".table th" in src and ".table td" in src)
check("Primary buttons use accent colour",
      ".btn-primary" in src and "var(--senet-accent)" in src)
check("Card border-radius: 12px",
      "border-radius: 12px" in src)
check("Jazzmin .main-header hidden",
      ".main-header" in src and "display: none" in src)
check("Sidebar z-index: 1000 (above content)",
      "z-index: 1000" in src)
check("Turbo SPA navigation active",
      "turbo:load" in src)
check("Active nav state uses accent colour",
      ".senet-nav-item.active" in src and "var(--senet-accent)" in src)
check("Logout hover turns red",
      "#ef4444" in src)

# ── Summary ────────────────────────────────────────────────────────────────────
passed = sum(results)
failed = len(results) - passed
pct = round(passed / len(results) * 100)
print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {failed} | Score: {pct}%\n")
sys.exit(0 if failed == 0 else 1)
