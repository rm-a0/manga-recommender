# MangaRec

Manga recommendation engine.

---

## Requirements

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Package and environment manager |
| PostgreSQL | 15+ (via Supabase) | Database |

## First-time setup

```bash
git clone https://github.com/rm-a0/manga-recommender
cd manga-recommender

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install base deps + dev tools (default for local development)
uv sync

# Copy env template and fill in your Supabase credentials
cp .env.example .env
```

## Running the app locally

```bash
# Start the API
uv run python main.py app

# API swagger docs
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/health
```

## Database migrations

Migrations use [Alembic](https://alembic.sqlalchemy.org/). Always run them against
the **direct connection** (`DATABASE_URL`), not the pooled URL.

```bash
# Apply all pending migrations (first run creates all tables)
uv run alembic upgrade head

# Create a new migration after editing src/db/models.py
uv run alembic revision --autogenerate -m "describe what changed"

# Check current state
uv run alembic current

# Roll back one migration
uv run alembic downgrade -1
```

> Migrations run automatically on Railway before the app starts (see `railway.toml`).
> For local development - run them manually.

## Ingestion pipeline

Pulls manga from the AniList GraphQL API and writes to the database.
This is a **one-shot offline job** - not triggered by the API.

```bash
# Install pipeline extras
uv sync --group pipeline

# Seed the database
uv run python main.py ingest

# Ingest fewer pages for a quick local test
uv run python main.py ingest --pages 5
```

---

## Dependency groups

Dependencies are split into groups so Docker only installs what the
production server actually needs. Add new packages to the **narrowest**
group that requires them.

| Group | When installed | What goes here |
|---|---|---|
| *(base)* | Always, including Docker | FastAPI, SQLAlchemy, runtime deps |
| `dev` | Local development | pytest, ruff, mypy, type stubs |
| `pipeline` | Running ingestion locally | rich, tenacity, throttle helpers |
| `ml` | Phase 2 model training | torch, faiss, sentence-transformers |

```bash
uv sync                  # base + dev  (default - use this locally)
uv sync --no-dev         # base only   (what Docker does)
uv sync --group pipeline # base + pipeline
uv sync --group ml       # base + ml
uv sync --all-groups     # everything
```

### Adding a dependency

```bash
# Runtime dep (goes in [project.dependencies] - will be in Docker)
uv add httpx

# Dev-only dep
uv add --group dev pytest-cov

# Pipeline dep
uv add --group pipeline rich

# ML dep
uv add --group ml torch
```

`uv add` updates both `pyproject.toml` and `uv.lock` automatically. Commit both files.

## Docker

The Docker image contains only **base dependencies** - no dev tools, no ML libs,
no data files. The database lives on Supabase; the container is stateless.

```bash
# Build
docker build -t mangarec .

# Run locally (mirrors production)
docker run --env-file .env -p 8000:8000 mangarec
```

> There is intentionally **no `docker-compose.yml`**. The database is managed (Supabase), so there is nothing to compose. One Dockerfile, one container.

## Deployment (Railway)

1. Push your repo to GitHub
2. Create a new Railway project → "Deploy from GitHub repo"
3. In Railway dashboard: **Variables → Add all variables from `.env.example`**
   - Set `DATABASE_URL` to the **pooled** Supabase URL (handles connection limits)
   - Set `DATABASE_URL_POOLED` to the same pooled URL
   - Set `APP_ENV=production` and `DEBUG=false`
   - Generate a strong `SECRET_KEY`
4. Railway reads `railway.toml` automatically — no further config needed
5. Every `git push` to `main` triggers a new deploy

The deploy sequence (defined in `railway.toml`):
```
build image → run alembic upgrade head → start API
```
If migrations fail, the deploy is aborted and the previous version stays live.

---

## Project structure

```
manga-recommender/
│
├── main.py                        # CLI entry point: app | ingest
│
├── src/
│   ├── config.py                  # Settings loaded from .env via pydantic-settings
│   │
│   ├── db/
│   │   ├── connection.py          # SQLAlchemy engine and session factory
│   │   ├── models.py              # ORM table definitions
│   │   └── migrations/            # Alembic migration files (auto-generated)
│   │
│   ├── ingestion/
│   │   ├── anilist.py             # AniList GraphQL client
│   │   ├── pipeline.py            # Orchestrates the full ingest run
│   │   └── normalizer.py          # Cleans and normalizes raw API data
│   │
│   ├── services/                  # Business logic — no HTTP, no SQL strings
│   │   ├── manga.py               # search_manga, get_manga, list_manga
│   │   ├── user.py                # create_user, get_list, update_entry
│   │   └── recommendation.py      # recommend_for_user, recommend_similar (Phase 1: placeholders)
│   │
│   └── api/
│       ├── main.py                # FastAPI app with lifespan and middleware
│       ├── routers/
│       │   ├── manga.py           # GET /manga/search, GET /manga/{id}
│       │   ├── users.py           # POST /users, GET /users/{id}/list
│       │   └── recommendations.py # GET /recommend/user/{id}, GET /recommend/similar/{id}
│       └── schemas.py             # Pydantic request and response models
│
├── tests/
│   ├── test_services/
│   └── test_api/
│
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── pyproject.toml                 # All deps and tool config live here
├── railway.toml                   # Railway deploy config
└── uv.lock                        # Commit this — pins exact versions
```

---

## Environment variable reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | Supabase direct connection — use for local dev and migrations |
| `DATABASE_URL_POOLED` | ✅ | Supabase transaction pooler — use in production |
| `APP_ENV` | ✅ | `development` or `production` |
| `DEBUG` | ✅ | `true` enables auto-reload and verbose errors |
| `SECRET_KEY` | ✅ | Random string for JWT signing — generate with `openssl rand -hex 32` |
| `API_HOST` | ✅ | Bind host — `0.0.0.0` for Docker/Railway |
| `API_PORT` | ✅ | Bind port — `8000` |
| `CORS_ORIGINS` | ✅ | Comma-separated allowed origins |
| `ANILIST_REQUEST_DELAY` | — | Seconds between AniList pages (default `0.7`) |
| `ANILIST_MAX_PAGES` | — | Pages to ingest (default `200`) |