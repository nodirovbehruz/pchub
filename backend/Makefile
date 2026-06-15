.PHONY: help build up down logs shell test migrate makemigrations collectstatic createsuperuser
.PHONY: build-prod up-prod down-prod logs-prod shell-prod restart-prod backup-db restore-db
.PHONY: ssl-setup monitoring-setup security-check deploy health-check

# Colors for output
YELLOW := \033[1;33m
GREEN := \033[0;32m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m

help:
	@echo "$(BLUE)PCHub Docker Commands$(NC)"
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@echo "  build             - Build Docker images"
	@echo "  up                - Start development environment"
	@echo "  down              - Stop development containers"
	@echo "  logs              - Show development container logs"
	@echo "  shell             - Open Django shell (development)"
	@echo "  test              - Run tests"
	@echo "  migrate           - Run database migrations (development)"
	@echo "  makemigrations    - Create new migrations"
	@echo "  collectstatic     - Collect static files"
	@echo "  createsuperuser   - Create Django superuser"
	@echo ""
	@echo "$(YELLOW)Production:$(NC)"
	@echo "  build-prod        - Build production Docker images"
	@echo "  up-prod           - Start production environment"
	@echo "  down-prod         - Stop production containers"
	@echo "  restart-prod      - Restart production services"
	@echo "  logs-prod         - Show production container logs"
	@echo "  shell-prod        - Open Django shell (production)"
	@echo "  deploy            - Full production deployment"
	@echo "  health-check      - Check production service health"
	@echo ""
	@echo "$(YELLOW)Database & Backup:$(NC)"
	@echo "  backup-db         - Create database backup"
	@echo "  restore-db        - Restore database from backup"
	@echo "  migrate-prod      - Run database migrations (production)"
	@echo ""
	@echo "$(YELLOW)Security & SSL:$(NC)"
	@echo "  ssl-setup         - Set up SSL certificates"
	@echo "  security-check    - Run security checks"
	@echo ""
	@echo "$(YELLOW)Monitoring:$(NC)"
	@echo "  monitoring-setup  - Set up monitoring stack"
	@echo "  cleanup           - Clean up unused Docker resources"

# Development commands
build:
	@echo "$(YELLOW)🔨 Building development images...$(NC)"
	cd docker/ && docker-compose build

up:
	@echo "$(YELLOW)🚀 Starting development environment...$(NC)"
	./scripts/docker-dev.sh

down:
	@echo "$(YELLOW)🛑 Stopping development containers...$(NC)"
	cd docker/ && docker-compose down

logs:
	@echo "$(YELLOW)📋 Showing development logs...$(NC)"
	cd docker/ && docker-compose logs -f

clean:
	@echo "$(YELLOW)🧹 Cleaning Python cache...$(NC)"
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete

shell:
	@echo "$(YELLOW)🐚 Opening Django shell (development)...$(NC)"
	cd docker/ && docker-compose exec web python manage.py shell

test:
	@echo "$(YELLOW)🧪 Running tests...$(NC)"
	cd docker/ && docker-compose exec web python manage.py test

migrate:
	@echo "$(YELLOW)🗄️ Running migrations (development)...$(NC)"
	cd docker/ && docker-compose exec web python manage.py migrate

makemigrations:
	@echo "$(YELLOW)📝 Creating migrations...$(NC)"
	cd docker/ && docker-compose exec web python manage.py makemigrations

collectstatic:
	@echo "$(YELLOW)📁 Collecting static files...$(NC)"
	cd docker/ && docker-compose exec web python manage.py collectstatic --noinput

createsuperuser:
	@echo "$(YELLOW)👤 Creating superuser...$(NC)"
	cd docker/ && docker-compose exec web python manage.py createsuperuser

# Production commands
build-prod:
	@echo "$(YELLOW)🔨 Building production images...$(NC)"
	cd docker/ && docker-compose -f docker-compose.prod.yml build

up-prod:
	@echo "$(YELLOW)🚀 Starting production environment...$(NC)"
	./scripts/docker-prod.sh

down-prod:
	@echo "$(YELLOW)🛑 Stopping production containers...$(NC)"
	cd docker/ && docker-compose -f docker-compose.prod.yml down

restart-prod:
	@echo "$(YELLOW)🔄 Restarting production services...$(NC)"
	cd docker/ && docker-compose -f docker-compose.prod.yml restart

logs-prod:
	@echo "$(YELLOW)📋 Showing production logs...$(NC)"
	cd docker/ && docker-compose -f docker-compose.prod.yml logs -f

shell-prod:
	@echo "$(YELLOW)🐚 Opening Django shell (production)...$(NC)"
	cd docker/ && docker-compose -f docker-compose.prod.yml exec web python manage.py shell

migrate-prod:
	@echo "$(YELLOW)🗄️ Running migrations (production)...$(NC)"
	cd docker/ && docker-compose -f docker-compose.prod.yml exec web python manage.py migrate

deploy: build-prod up-prod
	@echo "$(GREEN)✅ Production deployment completed!$(NC)"

health-check:
	@echo "$(YELLOW)🔍 Checking production service health...$(NC)"
	@curl -f http://localhost/health/ && echo "$(GREEN)✅ Web service is healthy$(NC)" || echo "$(RED)❌ Web service is unhealthy$(NC)"
	@cd docker/ && docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U pchub_user -d pchub && echo "$(GREEN)✅ Database is healthy$(NC)" || echo "$(RED)❌ Database is unhealthy$(NC)"
	@cd docker/ && docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping && echo "$(GREEN)✅ Redis is healthy$(NC)" || echo "$(RED)❌ Redis is unhealthy$(NC)"

# Database and backup commands
backup-db:
	@echo "$(YELLOW)💾 Creating database backup...$(NC)"
	@mkdir -p docker/db_backup
	cd docker/ && docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U pchub_user pchub > db_backup/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup created in docker/db_backup/$(NC)"

restore-db:
	@echo "$(RED)⚠️ This will restore the database from the latest backup!$(NC)"
	@read -p "Are you sure? [y/N]: " confirm && [ "$$confirm" = "y" ] || exit 1
	@LATEST_BACKUP=$$(ls -t docker/db_backup/backup_*.sql 2>/dev/null | head -n1); \
	if [ -z "$$LATEST_BACKUP" ]; then \
		echo "$(RED)❌ No backup files found!$(NC)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Restoring from: $$LATEST_BACKUP$(NC)"; \
	cd docker/ && cat ../$$LATEST_BACKUP | docker-compose -f docker-compose.prod.yml exec -T db psql -U pchub_user -d pchub
	@echo "$(GREEN)✅ Database restored successfully!$(NC)"

# SSL setup
ssl-setup:
	@echo "$(YELLOW)🔐 Setting up SSL certificates...$(NC)"
	@mkdir -p docker/ssl
	@echo "$(BLUE)Please place your SSL certificates in docker/ssl/:$(NC)"
	@echo "  - fullchain.pem (certificate + intermediate)"
	@echo "  - privkey.pem (private key)"
	@echo ""
	@echo "$(YELLOW)For Let's Encrypt, you can use:$(NC)"
	@echo "  certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com"
	@echo ""
	@echo "$(YELLOW)Then copy the certificates:$(NC)"
	@echo "  cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/"
	@echo "  cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/"

# Security check
security-check:
	@echo "$(YELLOW)🔒 Running security checks...$(NC)"
	@echo "$(BLUE)Checking for common security issues...$(NC)"
	@cd docker/ && docker-compose -f docker-compose.prod.yml exec web python manage.py check --deploy
	@echo "$(BLUE)Checking SSL configuration...$(NC)"
	@if [ -f docker/ssl/fullchain.pem ] && [ -f docker/ssl/privkey.pem ]; then \
		echo "$(GREEN)✅ SSL certificates found$(NC)"; \
	else \
		echo "$(YELLOW)⚠️ SSL certificates not found. Run 'make ssl-setup' first$(NC)"; \
	fi

# Monitoring setup
monitoring-setup:
	@echo "$(YELLOW)📊 Setting up monitoring...$(NC)"
	@echo "$(BLUE)Monitoring services are configured in docker-compose.prod.yml:$(NC)"
	@echo "  - Nginx metrics: http://localhost:9113/metrics"
	@echo "  - Application metrics: Configure in Django settings"
	@echo ""
	@echo "$(YELLOW)To add Prometheus + Grafana:$(NC)"
	@echo "1. Add monitoring services to docker-compose.prod.yml"
	@echo "2. Configure Prometheus to scrape metrics"
	@echo "3. Set up Grafana dashboards"

# Cleanup
cleanup:
	@echo "$(YELLOW)🧹 Cleaning up Docker resources...$(NC)"
	docker system prune -f
	docker volume prune -f
	docker network prune -f
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

# Environment validation
validate-env:
	@echo "$(YELLOW)🔍 Validating environment configuration...$(NC)"
	@if [ ! -f .env.prod ]; then \
		echo "$(RED)❌ .env.prod file not found!$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Environment configuration found$(NC)"

# Full deployment with checks
deploy-full: validate-env build-prod up-prod health-check
	@echo "$(GREEN)🎉 Full deployment completed successfully!$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "1. Configure your domain DNS to point to this server"
	@echo "2. Set up SSL certificates with 'make ssl-setup'"
	@echo "3. Configure monitoring with 'make monitoring-setup'"
	@echo "4. Set up automated backups"
	@echo "5. Review security settings with 'make security-check'"
