FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# --no-dev:             skip dev tools (pytest, ruff, mypy) - not needed at runtime
# --frozen:             fail if uv.lock is out of sync with pyproject.toml
# --no-install-project: deps only - the project's own source isn't copied in yet
# --no-cache:           keep image size down (uv cache isn't useful inside Docker)
RUN uv sync --no-dev --frozen --no-install-project --no-cache

COPY . .

# Second sync now installs the project itself (source is present). Cheap -
# dependencies are already resolved and cached from the layer above.
RUN uv sync --no-dev --frozen --no-cache

EXPOSE 8000

# Healthcheck for local Docker runs. Container Apps uses its own probes.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Runs uvicorn directly, not via the CLI - ingest is a separate offline job,
# never run in this container, so there's no shared-entrypoint reason to route
# through `manga_recommender`'s Typer app here.
#
# Invokes the baked venv's binary directly - `uv run uvicorn ...` would
# otherwise re-sync (pulling in dev deps and re-resolving against
# `.python-version`) on every container start, undoing --no-dev.
CMD ["/app/.venv/bin/uvicorn", "manga_recommender.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
