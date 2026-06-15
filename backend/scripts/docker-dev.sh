#!/bin/bash

# ==============================================================================
# PCHub Development Environment Manager
# ==============================================================================

# --- Styling Constants ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# --- Path Resolution ---
# Resolve the directory of this script, then get the project root (one level up)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
ENV_FILE="$PROJECT_ROOT/.env"

# --- Helper Functions ---

log_header() {
    echo -e "\n${BLUE}${BOLD}============================================================${NC}"
    echo -e "${CYAN}${BOLD}   $1${NC}"
    echo -e "${BLUE}${BOLD}============================================================${NC}"
}

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

check_requirements() {
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed."
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env file not found at: $ENV_FILE"
        log_warn "Please create it in the project root."
        exit 1
    fi
}

wait_for_db() {
    local service="db"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for database to accept connections..."

    cd "$DOCKER_DIR"
    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T $service pg_isready -U pchub_user -d pchub 2>/dev/null; then
            log_success "Database is ready!"
            return 0
        fi
        echo -ne "${YELLOW}   Attempt $attempt/$max_attempts...${NC}\r"
        sleep 2
        ((attempt++))
    done
    echo ""
    log_error "Database failed to start."
    return 1
}

create_superuser() {
    log_info "Ensuring default superuser exists..."
    docker compose exec -T web python manage.py shell << 'EOF'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u, e, p = 'admin', 'admin@pchub.com', 'admin123'
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, e, p)
    print('   >> Created superuser: admin')
else:
    print('   >> Superuser already exists')
EOF
}

# --- Main Execution ---

main() {
    log_header "🚀 Starting PCHub Development Environment"

    check_requirements

    # Setup Environment
    log_info "Setting up configuration..."
    cp "$ENV_FILE" "$DOCKER_DIR/.env"

    # Run Docker
    cd "$DOCKER_DIR"
    log_info "Building and starting containers..."
    docker compose up --build -d

    # Wait for DB
    wait_for_db || exit 1

    # Wait for Web
    log_info "Waiting for web application..."
    sleep 5

    # Migrations
    log_info "Running database migrations..."
    docker compose exec -T web python manage.py makemigrations || true
    docker compose exec -T web python manage.py migrate

    # Superuser
    create_superuser

    # Static Files
    log_info "Collecting static files..."
    docker compose exec -T web python manage.py collectstatic --noinput || true

    # Fixtures
    log_info "Checking for fixtures..."
    if docker compose exec -T web find . -name "*.json" -path "*/fixtures/*" | grep -q .; then
        docker compose exec -T web python manage.py loaddata */fixtures/*.json || log_warn "Some fixtures failed"
    fi

    # Final Report
    log_header "🎉 Environment Ready"

    echo -e "${BOLD}📍 Access Points:${NC}"
    echo -e "   🌐 App:        ${CYAN}http://localhost:8000${NC}"
    echo -e "   🔧 Admin:      ${CYAN}http://localhost:8000/admin${NC}"
    echo -e "   📚 API Docs:   ${CYAN}http://localhost:8000/api/schema/swagger/${NC}"
    echo -e ""
    echo -e "${BOLD}👤 Default Credentials:${NC}"
    echo -e "   User:      ${GREEN}admin${NC}"
    echo -e "   Pass:      ${GREEN}admin123${NC}"
}

# Run Script
main
