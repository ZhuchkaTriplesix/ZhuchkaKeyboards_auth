.PHONY: help install dev build up down logs clean test lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

dev: ## Start development environment
	docker compose -f docker/docker-compose.dev.yml up --build

build: ## Build production Docker image
	docker compose -f docker/docker-compose.yml build

up: ## Start production environment
	docker compose -f docker/docker-compose.yml up -d

down: ## Stop all containers
	docker compose -f docker/docker-compose.yml down
	docker compose -f docker/docker-compose.dev.yml down

logs: ## Show logs
	docker compose -f docker/docker-compose.yml logs -f

clean: ## Remove containers, volumes, and images
	docker compose -f docker/docker-compose.yml down -v --rmi all
	docker compose -f docker/docker-compose.dev.yml down -v --rmi all

test: ## Run tests
	pytest tests/ -v --cov=src --cov-report=html

lint: ## Run linter
	ruff check .

format: ## Format code
	ruff check --fix .
	ruff format .

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create a new migration
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

shell: ## Open Python shell with app context
	python -c "from src.main import app; import IPython; IPython.embed()"

db-shell: ## Open database shell
	docker exec -it fastapi-postgres psql -U postgres -d fastapi_db

redis-cli: ## Open Redis CLI
	docker exec -it fastapi-redis redis-cli

