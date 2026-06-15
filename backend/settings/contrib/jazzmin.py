from django.utils.translation import gettext_lazy as _

PCHUB_ADMIN_SETTINGS = {
    "SITE_HEADER": _("🎮 PCHub Gaming Control Center"),
    "SITE_TITLE": "PCHub Admin",
    "INDEX_TITLE": "Gaming Dashboard",
    "SITE_URL": "/",
    "SITE_URL": "/",
    "SHOW_POWERED_BY": False,
}

ADMIN_CHARTS_SETTINGS = {
    "enable_charts": True,
    "chart_library": "d3",  # Modern charts perfect for gaming dashboards
}

JAZZMIN_SETTINGS = {
    # Site branding
    "site_title": "PCHub Admin",
    "site_header": "🎮 PC HUB",
    "site_brand": "PC HUB",
    "site_logo": "admin/img/pchub-logo.svg",
    "login_logo": "admin/img/pchub-logo.svg",
    "welcome_sign": "Welcome to PCHub Gaming Admin",
    "copyright": "PCHub Gaming Platform © 2024",
    "user_avatar": "avatar",
    "topmenu_links": [
        {"name": "Dashboard", "url": "admin:index", "permissions": ["auth.view_user"]},
        {
            "name": "💳 Биллинг",
            "url": "admin:billing_computerbalance_changelist",
            "permissions": ["auth.view_user"],
        },
        {"name": "Site", "url": "/", "new_window": True},
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        # --- Billing ---
        "billing": "fas fa-credit-card",
        "billing.computerbalance": "fas fa-clock",
        "billing.payment": "fas fa-receipt",
        # --- Celery Results ---
        "django_celery_results": "fas fa-poll",  # App Icon
        "django_celery_results.groupresult": "fas fa-layer-group",
        "django_celery_results.taskresult": "fas fa-tasks",
        # --- Periodic Tasks (Celery Beat) ---
        "django_celery_beat": "fas fa-clock",  # App Icon
        "django_celery_beat.clockedschedule": "fas fa-history",
        "django_celery_beat.crontabschedule": "fas fa-calendar-alt",
        "django_celery_beat.intervalschedule": "fas fa-hourglass-half",
        "django_celery_beat.periodictask": "fas fa-sync-alt",
        "django_celery_beat.solarschedule": "fas fa-sun",
        # --- Token Blacklist ---
        "token_blacklist": "fas fa-shield-alt",  # App Icon
        "token_blacklist.blacklistedtoken": "fas fa-ban",
        "token_blacklist.outstandingtoken": "fas fa-file-contract",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "show_sidebar": True,
    "navigation_expanded": True,
    # CRITICAL: Link to the new CSS file
    "custom_css": "admin/css/pchub-admin.css",
    "custom_js": None,
    "show_ui_builder": False,  # Set to False for production
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    # DARK & NEON SETTINGS
    "brand_colour": "navbar-dark",  # Changed from light
    "accent": "accent-info",  # Changed to Info (Turquoise/Cyan)
    "navbar": "navbar-dark",  # Dark Navbar
    "no_navbar_border": True,  # Removes white border for glass look
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    # SIDEBAR SETTINGS
    "sidebar": "sidebar-dark-info",  # Dark sidebar with Cyan highlights
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,  # Compact matches gaming dashboards better
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    # THEME SETTING (CRITICAL)
    "theme": "darkly",  # Switches base to Dark Mode
    "dark_mode_theme": "darkly",
    # Button Mapping
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-outline-info",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": False,
    "sidebar_nav_accordion": True,
}
