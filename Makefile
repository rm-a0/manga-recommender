.DEFAULT_GOAL := help

# Prefer the `docker compose` plugin; fall back to the standalone `docker-compose`
# binary where the plugin isn't installed.
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

.PHONY: help setup test lint format typecheck migrate migration run-ingest run-app docker-build docker-run run db-up db-down clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Install deps and create .env from template if missing
	uv sync
	@[ -f .env ] || cp .env.example .env

test: ## Run the test suite
	uv run pytest

lint: ## Check formatting and lint rules
	uv run ruff check .

format: ## Auto-format code
	uv run ruff format .

typecheck: ## Run mypy
	uv run mypy src

migrate: ## Apply pending Alembic migrations
	uv run alembic upgrade head

migration: ## Create a new migration, e.g. make migration name="describe change"
	uv run alembic revision --autogenerate -m "$(name)"

run-app: ## Run the API locally
	uv run python -m manga_recommender app

run-ingest: ## Run the AniList ingestion pipeline (make run-ingest source=anilist, or all=1 for every source)
	uv run python -m manga_recommender ingest $(if $(all),--all,--source $(source))

docker-build: ## Build the production Docker image
	docker build -t mangarec .

docker-run: ## Run the Docker image locally (mirrors production)
	docker run --env-file .env -p 8000:8000 mangarec

run: ## Start the full local stack in Docker (Postgres + the app container)
	$(COMPOSE) up -d --build

db-up: ## Start local Postgres only (dev + test databases) - needed for tests
	$(COMPOSE) up -d --wait postgres

db-down: ## Stop all local containers (Postgres and/or the app)
	$(COMPOSE) down

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
