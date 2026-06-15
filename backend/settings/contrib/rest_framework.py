REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # SessionAuthentication removed: enforces CSRF for all POST requests
        # which conflicts with JWT-only React frontend (no CSRF token sent)
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Brute-force protection — applied via ScopedRateThrottle on sensitive views.
    "DEFAULT_THROTTLE_CLASSES": [
        # Backed by the dedicated 'throttle' cache (LocMem by default) so login
        # never 500s when Redis is down. See settings/throttling.py.
        "settings.throttling.CacheAnonRateThrottle",
        "settings.throttling.CacheScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",        # generic anonymous cap
        "login": "10/min",        # login attempts per IP
        "pc_register": "20/min",  # PC enrolment / token verify
    },
}
