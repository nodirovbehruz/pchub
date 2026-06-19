#!/bin/bash
set -e

echo "Starting PCHub Production..."

mkdir -p /app/logs /app/staticfiles /app/media

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Compiling translation messages..."
python manage.py compilemessages || echo "No locale files found, skipping translations."

echo "Starting Gunicorn (ASGI / Uvicorn workers — required for WebSocket/realtime)..."
# settings.asgi:application (ProtocolTypeRouter) + UvicornWorker is what makes the
# /ws/client/ WebSocket upgrade work. Plain gunicorn settings.wsgi:application is WSGI
# and returns HTTP 404 on the WS handshake, silently breaking chat / balance pushes /
# remote commands. With >1 worker the Redis channel layer (REDIS_CHANNELS_URL) is
# mandatory so group_send reaches clients on other workers.
exec gunicorn settings.asgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
