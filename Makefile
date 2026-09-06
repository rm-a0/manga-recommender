.DEFAULT_GOAL := help

# Prefer the `docker compose` plugin; fall back to the standalone `docker-compose`
# binary where the plugin isn't installed.
COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

.PHONY: help setup test lint format typecheck clean \
        migrate migration \
        serve ingest \
        ui ui-setup \
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
	uv run mypy backend

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

# --- Frontend ---

UI_DIR := frontend

# Set only when `api=` is passed. An unset run leaves the variable alone so the UI
# falls back to its own default (localhost:8000), or to a frontend/.env.local if
# one exists - an always-exported value would silently override that file.
UI_API := $(if $(api),API_BASE_URL=$(api))

ui-setup: ## Install the UI's npm dependencies
	npm --prefix $(UI_DIR) install

ui: ## Run the UI on :3000 against the local API, or a deployed one: make ui api=https://host
	@[ -d $(UI_DIR)/node_modules ] || $(MAKE) ui-setup
	$(UI_API) npm --prefix $(UI_DIR) run dev

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
