# Manga Recommender

Manga recommendation engine.

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

> **Not built yet.** `src/manga_recommender/__main__.py` is currently a stub — no CLI
> arg parsing, no FastAPI app. This is the target interface once the API layer exists.

```bash
# Start the API
uv run python -m manga_recommender app

# API swagger docs
open http://localhost:8000/docs

# Health check
curl http://localhost:8000/health
```

## Database migrations

Migrations use [Alembic](https://alembic.sqlalchemy.org/). Always run them against
the **direct connection** (`DB_URL`), not the pooled URL.

```bash
# Apply all pending migrations (first run creates all tables)
uv run alembic upgrade head

# Create a new migration after editing src/manga_recommender/db/models/
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

> **Pipeline logic done, CLI not wired up yet.** `AnilistExtractor` → `runner.py`
> (seeds the source, batches records, persists via `loader.py`) works end to end, but
> `src/manga_recommender/__main__.py` doesn't parse CLI args yet, so the commands
> below are the target interface, not runnable today.

```bash
# Install pipeline extras
uv sync --group pipeline

# Seed the database
uv run python -m manga_recommender ingest

# Limit pages for a quick local test (env var, not a CLI flag)
ANILIST_MAX_PAGES=5 uv run python -m manga_recommender ingest
```

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
   - Set `DB_URL` to the **pooled** Supabase URL (handles connection limits)
   - Set `DB_URL_POOLED` to the same pooled URL
   - Set `APP_ENV=production` and `APP_DEBUG=false`
4. Railway reads `railway.toml` automatically — no further config needed
5. Every `git push` to `main` triggers a new deploy

The deploy sequence (defined in `railway.toml`):
```
build image → run alembic upgrade head → start API
```
If migrations fail, the deploy is aborted and the previous version stays live.

## Project structure

Current state:

```
manga-recommender/
│
├── src/manga_recommender/
│   ├── __main__.py                 # CLI entry point (stub — arg parsing not wired up yet)
│   ├── config.py                  # Settings loaded from .env via pydantic-settings
│   │
│   ├── db/
│   │   ├── base.py                # Declarative Base + shared column helpers
│   │   └── models/
│   │       ├── manga.py           # Manga, MangaStatus
│   │       ├── genres.py          # Genre, manga_genres join table
│   │       ├── sources.py         # Source
│   │       ├── manga_external_ratings.py
│   │       └── users.py           # User, UserRole
│   │
│   └── ingestion/
│       ├── base.py                # BaseExtractor ABC, NormalizedMangaRecord
│       ├── anilist.py             # AniList GraphQL extractor
│       ├── registry.py            # source name -> extractor/default-weight mapping
│       ├── loader.py              # persists NormalizedMangaRecords to the database
│       └── runner.py              # seeds sources, batches extraction, calls loader
│
├── alembic/                        # Migrations (auto-generated via `make migration`)
│
├── .env.example
├── .gitignore
├── Dockerfile
├── Makefile
├── pyproject.toml                 # All deps and tool config live here
├── railway.toml                   # Railway deploy config
└── uv.lock                        # Commit this — pins exact versions
```

Not built yet: the `__main__.py` CLI (arg parsing) and the FastAPI `api`/`services`
layer. Planned shape for those, once they land:

```
├── src/manga_recommender/
│   ├── api/          # FastAPI app, routers, schemas
│   └── services/      # Business logic — no HTTP, no SQL strings
└── tests/
```

## Environment variable reference

| Variable | Required | Description |
|---|---|---|
| `DB_URL` | recommended | Direct Supabase connection — use for local dev and migrations |
| `DB_URL_POOLED` | recommended | Supabase transaction pooler — use in production |
| `APP_ENV` | — | `development` or `production` (default `development`) |
| `APP_DEBUG` | — | `true` enables verbose errors (default `true`) |
| `API_HOST` | — | Bind host — `0.0.0.0` for Docker/Railway (default `0.0.0.0`) |
| `API_PORT` | — | Bind port (default `8000`) |
| `ANILIST_REQUEST_DELAY` | — | Seconds between AniList pages (default `0.5`) |
| `ANILIST_MAX_PAGES` | — | Pages to ingest (default: unlimited) |
| `INGESTION_BATCH_SIZE` | — | Records per `load_batch` transaction (default `50`) |

Every variable has a fallback in `config.py`, so none are strictly required to boot —
`DB_URL`/`DB_URL_POOLED` are marked "recommended" because the fallback points at a
placeholder local Postgres, not a real database. `SECRET_KEY`/`CORS_ORIGINS` aren't
listed because auth and CORS aren't implemented yet.