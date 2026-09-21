# Jev AI - Makefile for development convenience

.PHONY: help build test run lint clean docker-up docker-down logs

help: ## Show this help message
	@echo "Jev AI - Common commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

build: ## Build all Docker images
	docker compose build

test: ## Run test suite with coverage
	cd jev-ai && pytest tests/ -v --cov=. --cov-report=term-missing

lint: ## Check imports and basic linting
	cd jev-ai && python -c "import main, config, wallet_tracker, copy_executor, telegram_handler, database, metrics"

run: ## Run orchestrator locally (requires .env)
	cd jev-ai && python main.py

clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	docker compose down -v

docker-up: ## Start all services in detached mode
	docker compose up -d

docker-down: ## Stop all services and remove volumes
	docker compose down -v

logs: ## Follow orchestrator logs
	docker compose logs -f jev-ai

ps: ## Show running containers
	docker compose ps

migrate: ## Run database migrations (placeholder)
	@echo "Database migrations handled by init.sql on first run"

coverage: ## Generate HTML coverage report
	cd jev-ai && pytest tests/ --cov=. --cov-report=html
	@echo "Coverage report: jev-ai/htmlcov/index.html"

# Default target
.DEFAULT_GOAL := help
