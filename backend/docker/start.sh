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

echo "Starting Gunicorn..."
exec gunicorn settings.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
