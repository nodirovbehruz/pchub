from django.apps import AppConfig


class SessionsConfig(AppConfig):
    """Sessions app — client sessions, reviews, admin calls.

    Name is `sessions_` (with underscore) to avoid clash with django.contrib.sessions.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sessions_"
    label = "club_sessions"
    verbose_name = "Club Sessions"
