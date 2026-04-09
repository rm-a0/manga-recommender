FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# --no-dev:   skip dev tools (pytest, ruff, mypy) - not needed at runtime
# --frozen:   fail if uv.lock is out of sync with pyproject.toml
# --no-cache: keep image size down (uv cache isn't useful inside Docker)
RUN uv sync --no-dev --frozen --no-cache

COPY . .

EXPOSE 8000

# Healthcheck so Railway / Docker knows when the app is ready.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uv", "run", "python", "main.py", "app"]