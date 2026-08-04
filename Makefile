.DEFAULT_GOAL := help

.PHONY: help setup dev test lint format typecheck migrate migration ingest docker-build docker-run clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Install deps and create .env from template if missing
	uv sync
	@[ -f .env ] || cp .env.example .env

dev: ## Run the API locally
	uv run python main.py app

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

ingest: ## Run the AniList ingestion pipeline
	uv run python main.py ingest

docker-build: ## Build the production Docker image
	docker build -t mangarec .

docker-run: ## Run the Docker image locally (mirrors production)
	docker run --env-file .env -p 8000:8000 mangarec

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
