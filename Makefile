.DEFAULT_GOAL := help

# Prefer the `docker compose` plugin; fall back to the standalone `docker-compose`
# binary where the plugin isn't installed.
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

.PHONY: help setup test lint format typecheck clean \
        migrate migration \
        serve ingest \
        docker-build docker-run db-up stack down

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Install deps and create .env from template if missing
	uv sync
	@[ -f .env ] || cp .env.example .env

# --- Code quality ---

test: ## Run the test suite
	uv run pytest

lint: ## Check formatting and lint rules
	uv run ruff check .
	uv run ruff format --check .

format: ## Auto-format code
	uv run ruff format .

typecheck: ## Run mypy
	uv run mypy src

# --- Database (Alembic) ---

migrate: ## Apply pending Alembic migrations
	uv run alembic upgrade head

migration: ## Create a new migration, e.g. make migration name="describe change"
	uv run alembic revision --autogenerate -m "$(name)"

# --- Run on the host (no Docker) ---

serve: ## Run the API on the host
	uv run python -m manga_recommender app

ingest: ## Run the AniList ingestion pipeline (make ingest source=anilist, or all=1 for every source)
	uv run python -m manga_recommender ingest $(if $(all),--all,--source $(source))

# --- Docker ---

docker-build: ## Build the production image (no Postgres - mirrors Railway)
	docker build -t mangarec .

docker-run: ## Run the production image standalone (mirrors Railway; uses .env's DB_URL as-is)
	docker run --env-file .env -p 8000:8000 mangarec

db-up: ## Start local Postgres only, for local dev (tests spin up their own container)
	$(COMPOSE) up -d --wait postgres

stack: ## Start the full local stack in Docker Compose (Postgres + the app)
	$(COMPOSE) up -d --build

down: ## Stop all local Compose containers, whichever are running
	$(COMPOSE) down

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
