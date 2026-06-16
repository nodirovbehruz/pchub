"""pytest bootstrap — set the env vars that settings.settings reads at import time,
BEFORE Django (or pytest-django) touches the settings module. Runs first because
pytest imports the rootdir conftest before accessing DJANGO_SETTINGS_MODULE.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "*")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
