#!/bin/bash

# =============================================================================
# PCHub Backend - Deployment & Management Script
# Usage: ./deploy.sh [command] [options]
# =============================================================================

set -e

# ---- Config ----
COMPOSE_FILE="docker/docker-compose.prod.ip.yml"
APP_CONTAINER="web"
PROJECT_NAME="pchub_prod"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log()    { echo -e "${GREEN}[✔] $1${NC}"; }
warn()   { echo -e "${YELLOW}[!] $1${NC}"; }
error()  { echo -e "${RED}[✘] $1${NC}"; exit 1; }
info()   { echo -e "${BLUE}[i] $1${NC}"; }
step()   { echo -e "${CYAN}[→] $1${NC}"; }

# ---- Helpers ----
check_env() {
    if [ ! -f ".env" ]; then
        error ".env file not found. Copy .env.example to .env and fill in values."
    fi
}

dc() {
    docker compose -f "$COMPOSE_FILE" --env-file .env -p "$PROJECT_NAME" "$@"
}

# =============================================================================
# COMMANDS
# =============================================================================

cmd_deploy() {
    check_env
    step "Starting full deployment..."

    # Create required directories
    mkdir -p docker/logs docker/db_backup

    step "Pulling latest base images..."
    dc pull --ignore-buildable

    step "Building images..."
    dc build --no-cache

    step "Starting all services..."
    dc up -d

    log "Deployment complete!"
    echo ""
    cmd_status
}

cmd_update() {
    check_env
    step "Updating deployment (git pull + rebuild + restart)..."

    step "Pulling latest code..."
    git pull

    step "Building new images..."
    dc build --no-cache

    step "Recreating containers with zero downtime..."
    dc up -d --force-recreate

    log "Update complete!"
    echo ""
    cmd_status
}

cmd_start() {
    check_env
    step "Starting services..."
    dc up -d
    log "Services started."
    cmd_status
}

cmd_stop() {
    step "Stopping all services..."
    dc stop
    log "All services stopped."
}

cmd_down() {
    warn "This will stop and remove containers (volumes are preserved)."
    read -p "Continue? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }
    dc down
    log "Containers removed."
}

cmd_restart() {
    SERVICE=${1:-}
    if [ -n "$SERVICE" ]; then
        step "Restarting $SERVICE..."
        dc restart "$SERVICE"
    else
        step "Restarting all services..."
        dc restart
    fi
    log "Restart complete."
}

cmd_build() {
    check_env
    step "Building images..."
    dc build --no-cache
    log "Build complete."
}

cmd_migrate() {
    step "Running database migrations..."
    dc exec "$APP_CONTAINER" python manage.py migrate --noinput
    log "Migrations complete."
}

cmd_makemigrations() {
    APP=${1:-}
    step "Making migrations${APP:+ for $APP}..."
    dc exec "$APP_CONTAINER" python manage.py makemigrations $APP
    log "Makemigrations complete."
}

cmd_collectstatic() {
    step "Collecting static files..."
    dc exec "$APP_CONTAINER" python manage.py collectstatic --noinput --clear
    log "Static files collected."
}

cmd_createsuperuser() {
    step "Creating superuser from environment variables..."
    dc exec "$APP_CONTAINER" python manage.py createsuperuser \
        --noinput \
        --username "${DJANGO_SUPERUSER_USERNAME:-admin}" \
        --email "${DJANGO_SUPERUSER_EMAIL:-admin@pchub.com}" || \
    dc exec "$APP_CONTAINER" python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = '${DJANGO_SUPERUSER_USERNAME:-admin}'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, '${DJANGO_SUPERUSER_EMAIL:-admin@pchub.com}', '${DJANGO_SUPERUSER_PASSWORD:-admin123}')
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
    log "Done."
}

cmd_logs() {
    SERVICE=${1:-}
    LINES=${2:-100}
    if [ -n "$SERVICE" ]; then
        dc logs -f --tail="$LINES" "$SERVICE"
    else
        dc logs -f --tail="$LINES"
    fi
}

cmd_status() {
    echo ""
    info "=== Container Status ==="
    dc ps
    echo ""
}

cmd_shell() {
    step "Opening Django shell..."
    dc exec "$APP_CONTAINER" python manage.py shell
}

cmd_bash() {
    SERVICE=${1:-$APP_CONTAINER}
    step "Opening bash in $SERVICE..."
    dc exec "$SERVICE" bash || dc exec "$SERVICE" sh
}

cmd_backup() {
    check_env
    source .env
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="docker/db_backup"
    BACKUP_FILE="$BACKUP_DIR/pchub_backup_$TIMESTAMP.sql"

    mkdir -p "$BACKUP_DIR"
    step "Backing up database to $BACKUP_FILE..."
    dc exec -T db pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE"
    gzip "$BACKUP_FILE"
    log "Backup saved: ${BACKUP_FILE}.gz"
}

cmd_restore() {
    BACKUP_FILE=${1:-}
    [ -z "$BACKUP_FILE" ] && error "Usage: ./deploy.sh restore <backup_file.sql.gz>"
    [ -f "$BACKUP_FILE" ] || error "File not found: $BACKUP_FILE"

    source .env
    warn "This will overwrite the current database!"
    read -p "Continue? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }

    step "Restoring from $BACKUP_FILE..."
    gunzip -c "$BACKUP_FILE" | dc exec -T db psql -U "$DB_USER" "$DB_NAME"
    log "Restore complete."
}

cmd_dbshell() {
    source .env 2>/dev/null || true
    step "Opening PostgreSQL shell..."
    dc exec db psql -U "${DB_USER:-pchub_user}" "${DB_NAME:-pchub}"
}

cmd_check() {
    step "Running Django system checks..."
    dc exec "$APP_CONTAINER" python manage.py check
    log "All checks passed."
}

cmd_flush() {
    warn "This will DELETE all data in the database!"
    read -p "Are you sure? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || { info "Aborted."; exit 0; }
    dc exec "$APP_CONTAINER" python manage.py flush --noinput
    log "Database flushed."
}

cmd_setup() {
    info "=== First-time setup ==="
    check_env
    mkdir -p docker/logs docker/db_backup

    step "Building images..."
    dc build --no-cache

    step "Starting database and redis first..."
    dc up -d db redis

    step "Waiting for database to be ready (30s)..."
    sleep 30

    step "Starting all services..."
    dc up -d

    step "Waiting for web to start (20s)..."
    sleep 20

    step "Running migrations..."
    dc exec "$APP_CONTAINER" python manage.py migrate --noinput

    step "Collecting static files..."
    dc exec "$APP_CONTAINER" python manage.py collectstatic --noinput --clear

    step "Creating superuser..."
    cmd_createsuperuser

    log "Setup complete!"
    echo ""
    cmd_status
}

cmd_help() {
    echo ""
    echo -e "${CYAN}PCHub Backend - Deployment Script${NC}"
    echo ""
    echo "Usage: ./deploy.sh <command> [options]"
    echo ""
    echo -e "${YELLOW}Deployment:${NC}"
    echo "  setup              First-time full setup (build + migrate + superuser)"
    echo "  deploy             Build images and start all services"
    echo "  update             git pull + rebuild + restart (for updates)"
    echo "  build              Build Docker images only"
    echo ""
    echo -e "${YELLOW}Service Control:${NC}"
    echo "  start              Start all stopped services"
    echo "  stop               Stop all running services"
    echo "  restart [service]  Restart all or a specific service"
    echo "  down               Stop and remove containers"
    echo "  status             Show container status"
    echo ""
    echo -e "${YELLOW}Django Management:${NC}"
    echo "  migrate            Run database migrations"
    echo "  makemigrations [app]  Make new migrations"
    echo "  collectstatic      Collect static files"
    echo "  createsuperuser    Create superuser from .env"
    echo "  check              Run Django system checks"
    echo "  flush              Flush all database data (DANGER)"
    echo ""
    echo -e "${YELLOW}Database:${NC}"
    echo "  backup             Backup PostgreSQL database"
    echo "  restore <file>     Restore from a .sql.gz backup file"
    echo "  dbshell            Open PostgreSQL interactive shell"
    echo ""
    echo -e "${YELLOW}Debugging:${NC}"
    echo "  logs [service] [lines]  Follow logs (default: all, 100 lines)"
    echo "  shell              Open Django Python shell"
    echo "  bash [service]     Open bash in container (default: web)"
    echo ""
    echo -e "${YELLOW}Services:${NC}"
    echo "  web | db | redis | nginx | celery_worker | celery_beat"
    echo ""
}

# =============================================================================
# ENTRYPOINT
# =============================================================================

COMMAND=${1:-help}
shift || true

case "$COMMAND" in
    setup)           cmd_setup ;;
    deploy)          cmd_deploy ;;
    update)          cmd_update ;;
    build)           cmd_build ;;
    start)           cmd_start ;;
    stop)            cmd_stop ;;
    restart)         cmd_restart "$@" ;;
    down)            cmd_down ;;
    status)          cmd_status ;;
    migrate)         cmd_migrate ;;
    makemigrations)  cmd_makemigrations "$@" ;;
    collectstatic)   cmd_collectstatic ;;
    createsuperuser) cmd_createsuperuser ;;
    check)           cmd_check ;;
    flush)           cmd_flush ;;
    backup)          cmd_backup ;;
    restore)         cmd_restore "$@" ;;
    dbshell)         cmd_dbshell ;;
    logs)            cmd_logs "$@" ;;
    shell)           cmd_shell ;;
    bash)            cmd_bash "$@" ;;
    help|--help|-h)  cmd_help ;;
    *)               error "Unknown command: $COMMAND. Run ./deploy.sh help" ;;
esac
