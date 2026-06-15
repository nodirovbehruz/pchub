import os

from django.core.asgi import get_asgi_application

# NOTE: the settings module is the PACKAGE `settings` (settings/__init__.py),
# which loads settings.py PLUS contrib/* (DRF, JWT). Using "settings.settings"
# would skip contrib and break JWT auth.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

# Initialise Django before importing anything that touches the app registry.
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from realtime.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
