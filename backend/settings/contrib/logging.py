import os

# Check if file logging should be disabled
DISABLE_FILE_LOGGING = os.getenv("DISABLE_FILE_LOGGING", "False").lower() == "true"
USE_CONSOLE_LOGGING = os.getenv("LOGGING_USE_CONSOLE", "False").lower() == "true"

if DISABLE_FILE_LOGGING or USE_CONSOLE_LOGGING:
    # Console-only logging for production Docker environments
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "root": {
            "handlers": ["console"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console"],
                "level": "ERROR",
                "propagate": False,
            },
            "django.security": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "celery": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
else:
    # File + console logging for development
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
                "style": "{",
            },
            "simple": {
                "format": "{levelname} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.getenv("LOG_FILE", "/app/logs/django.log"),
                "maxBytes": 1024 * 1024 * 15,  # 15MB
                "backupCount": 10,
                "formatter": "verbose",
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "root": {
            "handlers": ["console", "file"],
            "level": os.getenv("LOG_LEVEL", "INFO"),
        },
        "loggers": {
            "django": {
                "handlers": ["console", "file"],
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console", "file"],
                "level": "ERROR",
                "propagate": False,
            },
            "django.security": {
                "handlers": ["console", "file"],
                "level": "WARNING",
                "propagate": False,
            },
            "celery": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False,
            },
        },
    }
