#!/bin/bash

# ==============================================================================
# PCHub Production Deployment Manager
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
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="docker-compose.prod.yml"

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

cleanup() {
    echo ""
    log_warn "🛑 Interrupt received! Cleaning up..."
    cd "$DOCKER_DIR"
    docker compose -f $COMPOSE_FILE down --remove-orphans 2>/dev/null || true
    log_success "Cleanup completed. Exiting."
    exit 130
}

# Set up signal trapping
trap cleanup SIGINT SIGTERM

check_requirements() {
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Configuration file not found: $ENV_FILE"
        exit 1
    fi
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed."
        exit 1
    fi
}

setup_ssl() {
    local domain="$1"
    local email="${2:-admin@${domain}}"

    log_header "🔒 SSL Setup: $domain"

    cd "$DOCKER_DIR"

    # Nginx Configuration Update
    if [ -f "nginx.conf" ] && ! grep -q "ssl_certificate" nginx.conf; then
        log_info "Updating nginx configuration..."
        cp nginx.conf nginx.conf.backup
        sed -i "s/yourdomain\.com/$domain/g" nginx.conf
        sed -i "s/www\.yourdomain\.com/www.$domain/g" nginx.conf
        log_success "Nginx config updated."
    fi

    # Determine Domains
    log_info "Requesting certificate for: $domain"
    if [[ "$domain" == *.*.* ]]; then
        DOMAINS=(-d "$domain") # Subdomain
    else
        DOMAINS=(-d "$domain" -d "www.$domain") # Root domain
    fi

    # Run Certbot
    if docker compose -f $COMPOSE_FILE run --rm certbot \
        certonly --webroot --webroot-path=/var/www/certbot \
        --email "$email" --agree-tos --no-eff-email --force-renewal \
        "${DOMAINS[@]}"; then

        log_success "Certificate generated!"

        log_info "Reloading Nginx..."
        docker compose -f $COMPOSE_FILE restart nginx

        log_info "Setting up auto-renewal..."
        CRON_CMD="0 12 * * * cd $DOCKER_DIR && docker compose -f $COMPOSE_FILE run --rm certbot renew --quiet && docker compose -f $COMPOSE_FILE restart nginx"
        (crontab -l 2>/dev/null | grep -v "certbot renew"; echo "$CRON_CMD") | crontab -
        log_success "Auto-renewal scheduled."
    else
        log_error "SSL generation failed."
        echo -e "${YELLOW}Check: 1. DNS points to this IP. 2. Firewall ports 80/443 open.${NC}"
        return 1
    fi
}

# --- Main Logic ---

handle_commands() {
    cd "$DOCKER_DIR"
    case "$1" in
        stop)
            log_info "Stopping containers..."
            docker compose -f $COMPOSE_FILE down --remove-orphans
            log_success "Stopped."
            exit 0 ;;
        logs)
            log_info "Fetching logs..."
            if [ -n "$2" ]; then
                docker compose -f $COMPOSE_FILE logs "$2" --tail=100
            else
                docker compose -f $COMPOSE_FILE logs --tail=100
            fi
            exit 0 ;;
        ssl)
            if [ -z "$2" ]; then
                log_error "Usage: $0 ssl <domain> [email]"
                exit 1
            fi
            setup_ssl "$2" "$3"
            exit $? ;;
        renew-ssl)
            log_info "Renewing certificates..."
            docker compose -f $COMPOSE_FILE run --rm certbot renew
            docker compose -f $COMPOSE_FILE restart nginx
            log_success "Done."
            exit 0 ;;
        *)
            if [ -n "$1" ]; then
                log_error "Unknown command: $1"
                echo "Available: stop, logs, ssl, renew-ssl"
                exit 1
            fi
            ;;
    esac
}

deploy_app() {
    log_header "🚀 Starting PCHub Production Deployment"
    log_info "Project Root: $PROJECT_ROOT"

    check_requirements

    # Setup Docker Directory
    log_info "Preparing directories and environment..."
    mkdir -p "$DOCKER_DIR/logs" "$DOCKER_DIR/db_backup" "$DOCKER_DIR/ssl"
    chmod 777 "$DOCKER_DIR/logs"
    cp "$ENV_FILE" "$DOCKER_DIR/.env"

    cd "$DOCKER_DIR"

    # Start DB & Redis
    log_info "Starting database services..."
    docker compose -f $COMPOSE_FILE up -d db redis

    # Health Check
    log_info "Waiting for database..."
    for i in {1..10}; do
        if docker compose -f $COMPOSE_FILE exec -T db pg_isready -U ${DB_USER:-pchub_user} >/dev/null 2>&1; then
            log_success "DB Connected."
            break
        fi
        sleep 5
    done

    # Start Web
    log_info "Building web application..."
    docker compose -f $COMPOSE_FILE up -d --build web

    # Django Operations
    log_info "Running system checks..."
    docker compose -f $COMPOSE_FILE exec -T web python manage.py migrate --noinput
    docker compose -f $COMPOSE_FILE exec -T web python manage.py collectstatic --noinput --clear

    # Full Start
    log_info "Starting Nginx and remaining services..."
    docker compose -f $COMPOSE_FILE up -d

    # Final Summary
    log_header "🎉 Deployment Complete"

    # Get Public IP (Optional, fallback to localhost)
    PUBLIC_IP=$(curl -s ifconfig.me || echo "localhost")

    echo -e "${BOLD}📊 Service Status:${NC}"
    docker compose -f $COMPOSE_FILE ps db redis web nginx --format "table {{.Service}}\t{{.State}}\t{{.Status}}"

    echo -e "\n${BLUE}🌐 URLs:${NC}"
    echo -e "   Web:    ${GREEN}http://$PUBLIC_IP${NC}"
    echo -e "   Admin:  ${GREEN}http://$PUBLIC_IP/admin${NC}"

    echo -e "\n${BLUE}🛠  Management Commands:${NC}"
    echo -e "   SSL:    ${CYAN}./scripts/docker-prod.sh ssl <domain>${NC}"
    echo -e "   Logs:   ${CYAN}./scripts/docker-prod.sh logs${NC}"
    echo -e "   Stop:   ${CYAN}./scripts/docker-prod.sh stop${NC}"
}

# --- Execute ---

# Check if arguments provided (commands like stop, ssl, etc)
if [ $# -gt 0 ]; then
    handle_commands "$@"
else
    # No args? Run deployment
    deploy_app
fi
