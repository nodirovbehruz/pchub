import os
from pathlib import Path

from .environment import env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def rel(*path):
    return BASE_DIR.joinpath(*path)


SECRET_KEY = env.str("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Was unset → Django default "America/Chicago", which skewed day/night tariff hour
# logic and every hourly/date-range analytic by ~10-11h from the clubs' real timezone.
TIME_ZONE = env.str("TIME_ZONE", default="Asia/Tashkent")
USE_TZ = True

if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
    SESSION_COOKIE_SAMESITE = env.str("SESSION_COOKIE_SAMESITE", default="Lax")
    CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
    CSRF_COOKIE_SAMESITE = env.str("CSRF_COOKIE_SAMESITE", default="Lax")
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False
    )
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)

# Application definition
ADMIN_APPS = [
    "jazzmin",
]

AUTH_USER_MODEL = "accounts.CustomUser"

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    # API & Documentation
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    # CORS & Security
    "corsheaders",
    # Database & Caching
    "django_redis",
    # Async & WebSocket
    "channels",
    "graphene_django",
    
    # Utilities
    "django_extensions",
    "django_filters",
    "phonenumber_field",
    "imagekit",
    # Development Tools
    "django_celery_beat",
    "django_celery_results",
]

DEBUG_APPS = []
if DEBUG:
    DEBUG_APPS = [
        "debug_toolbar",
        "silk",
    ]

LOCAL_APPS = [
    "apps.accounts",
    "apps.shops",
    "apps.games",
    "apps.computers",
    "apps.billing.apps.BillingConfig",
    "apps.clubs.apps.ClubsConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.sessions_.apps.SessionsConfig",
    "apps.loyalty.apps.LoyaltyConfig",
    "apps.content.apps.ContentConfig",
    "apps.integrations.apps.IntegrationsConfig",
]

INSTALLED_APPS = ADMIN_APPS + DJANGO_APPS + LOCAL_APPS + THIRD_PARTY_APPS + DEBUG_APPS

# Base middleware
BASE_MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "apps.accounts.middleware.UpdateLastActivityMiddleware",
    "apps.clubs.middleware.ClubTenantMiddleware",
    "apps.clubs.middleware.SubscriptionGateMiddleware",
]

# Debug middleware (only in DEBUG mode)
DEBUG_MIDDLEWARE = []
if DEBUG:
    DEBUG_MIDDLEWARE = [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
        "silk.middleware.SilkyMiddleware",
    ]

MIDDLEWARE = BASE_MIDDLEWARE + DEBUG_MIDDLEWARE

ROOT_URLCONF = "settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [rel("templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "settings.wsgi.application"
ASGI_APPLICATION = "settings.asgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.str("DB_NAME"),
        "USER": env.str("DB_USER"),
        "PASSWORD": env.str("DB_PASSWORD"),
        "HOST": env.str("DB_HOST"),
        "PORT": env.str("DB_PORT"),
    },
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 4,
        },
    },
]

LOCALE_PATHS = [BASE_DIR / "locale"]

# Static files (CSS, JavaScript, Images)
STATIC_URL = env.str("PCHUB_STATIC_URL", default="/static/")
STATIC_ROOT = rel("staticfiles")

STATICFILES_DIRS = (BASE_DIR / "assets",)

# Media files
MEDIA_URL = env.str("PCHUB_MEDIA_URL", default="/media/")
MEDIA_ROOT = env.str("PCHUB_MEDIA_ROOT", default=BASE_DIR / "media")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis Configuration
REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")

# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "PICKLE_VERSION": -1,
        },
    },
    # Dedicated cache for DRF rate-limiting. Uses local memory by default so
    # brute-force protection works even when Redis is unavailable (dev) and a
    # cache outage can never 500 the login endpoint. Point THROTTLE_CACHE_URL at
    # Redis in production if you want throttle counters shared across workers.
    "throttle": (
        {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env.str("THROTTLE_CACHE_URL"),
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
        if env.str("THROTTLE_CACHE_URL", default="")
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "pchub-throttle",
        }
    ),
}


# Cache key prefix
CACHE_KEY_PREFIX = env.str("CACHE_KEY_PREFIX", default="pchub")

# # Cache timeout settings
CACHE_TIMEOUT = {
    "default": 60 * 15,  # 15 minutes
    "long": 60 * 60 * 24,  # 24 hours
    "short": 60 * 5,  # 5 minutes
}

# Channels layer.
# Dev default: in-memory (no Redis dependency, single-process). With MULTIPLE uvicorn
# workers the in-memory layer is per-process, so group_send (chat, balance pushes,
# remote commands) never reaches a client connected to another worker — realtime
# silently breaks. Fall back to the already-configured REDIS_URL when a dedicated
# REDIS_CHANNELS_URL isn't set, so realtime works out-of-the-box wherever Redis exists.
_CHANNELS_REDIS = env.str("REDIS_CHANNELS_URL", default="") or env.str("REDIS_URL", default="")
if _CHANNELS_REDIS:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_CHANNELS_REDIS], "capacity": 1500, "expiry": 10},
        },
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    }


CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Celery task routing (optional but recommended)
CELERY_TASK_ROUTES = {
    "apps.game_servers.tasks.match_tasks.*": {"queue": "matches"},
    "apps.game_servers.tasks.monitoring_tasks.*": {"queue": "monitoring"},
    "apps.game_servers.tasks.result_tasks.*": {"queue": "results"},
}


X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

# CORS Configuration — allow React dev server (all Vite ports)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:5177",
    "http://localhost:5178",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5176",
])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False  # explicit

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[
    "http://localhost:5173",  # Vite dev server
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5175",
])
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = env.str("CSRF_COOKIE_SAMESITE", default="Lax")
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
CSRF_USE_SESSIONS = False
CSRF_COOKIE_NAME = "csrftoken"

# Create necessary directories
os.makedirs(BASE_DIR / "logs", exist_ok=True)
os.makedirs(BASE_DIR / "media", exist_ok=True)
os.makedirs(BASE_DIR / "staticfiles", exist_ok=True)

FEATURES = env.list("FEATURES", default=[])

# Email Configuration
EMAIL_BACKEND = env.str(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env.str("EMAIL_HOST", default="mailpit")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="noreply@pchub.local")

# Email timeout settings
EMAIL_TIMEOUT = 10

# Admin Interface Settings (Jazzmin)
from settings.contrib.jazzmin import *

# GraphQL Configuration
GRAPHENE = {
    "SCHEMA": "settings.schema.schema",
    "MIDDLEWARE": [
        "apps.accounts.middleware.GrapheneJWTAuthenticationMiddleware",
        "graphene_django.debug.DjangoDebugMiddleware",
    ]
}
