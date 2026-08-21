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

The CLI is wired up. The FastAPI app itself isn't built yet — `app` currently just
raises `NotImplementedError`.

```bash
uv run python -m manga_recommender ingest --source anilist   # run ingestion
uv run python -m manga_recommender app                        # not implemented yet
```

## Database migrations

Migrations use [Alembic](https://alembic.sqlalchemy.org/). Always run them against
the **direct connection** (`DB_URL`), not the pooled URL.

```bash
uv run alembic upgrade head                                        # apply all pending
uv run alembic revision --autogenerate -m "describe what changed"  # after model changes
uv run alembic current                                             # check current state
uv run alembic downgrade -1                                        # roll back one
```

> Migrations run automatically on Railway before the app starts (see `railway.toml`).
> For local development, run them manually.

## Ingestion pipeline

Pulls manga from the AniList GraphQL API and writes to the database. A **one-shot
offline job**, not triggered by the API. Walks AniList's raw ID space in concurrent,
rate-limited `id_in` chunk requests rather than paginating, since AniList's
page-based pagination caps out at 5,000 results.

```bash
uv sync --group pipeline                                     # install pipeline extras
uv run python -m manga_recommender ingest --source anilist   # full catalogue

# Small test run, capped to a handful of chunks instead of the whole catalogue
ANILIST_MAX_ID=30201 uv run python -m manga_recommender ingest --source anilist
```

A full run currently fetches in roughly ~2 hours (bounded by AniList's rate limit).
Loading used to be far slower than that; bulk manga/genre writes brought it down to
roughly ~4.5-5 hours, still the slower half of the pipeline — see `TODO.md` for the
remaining ratings bulk-upsert work.

## Dependency groups

Dependencies are split into groups so Docker only installs what the
production server actually needs. Add new packages to the **narrowest**
group that requires them.

| Group | When installed | What goes here |
|---|---|---|
| *(base)* | Always, including Docker | FastAPI, SQLAlchemy, runtime deps |
| `dev` | Local development | pytest, ruff, mypy, type stubs |
| `pipeline` | Running ingestion locally | httpx, aiolimiter, structlog |
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
uv add httpx                    # runtime dep (goes in [project.dependencies])
uv add --group dev pytest-cov   # dev-only dep
uv add --group pipeline rich    # pipeline dep
uv add --group ml torch         # ML dep
```

`uv add` updates both `pyproject.toml` and `uv.lock` automatically. Commit both files.

## Docker

The Docker image contains only **base dependencies** - no dev tools, no ML libs,
no data files. The database lives on Supabase; the container is stateless.

```bash
docker build -t mangarec .
docker run --env-file .env -p 8000:8000 mangarec
```

> There is intentionally **no `docker-compose.yml`**. The database is managed
> (Supabase), so there is nothing to compose. One Dockerfile, one container.

## Deployment (Railway)

1. Push your repo to GitHub
2. Create a new Railway project → "Deploy from GitHub repo"
3. In Railway dashboard: **Variables → Add all variables from `.env.example`**
   - Set `DB_URL` to the **pooled** Supabase URL (handles connection limits)
   - Set `DB_URL_POOLED` to the same pooled URL
   - Set `APP_ENV=production` and `APP_DEBUG=false`
4. Railway reads `railway.toml` automatically — no further config needed
5. Every `git push` to `main` triggers a new deploy:
   `build image → run alembic upgrade head → start API`. If migrations fail, the
   deploy is aborted and the previous version stays live.

## Project structure

```
manga-recommender/
│
├── src/manga_recommender/
│   ├── __main__.py             # CLI entry point
│   ├── cli.py                  # Typer app: `ingest`, `app` (not implemented)
│   ├── config.py                # Settings loaded from .env via pydantic-settings
│   ├── logging_config.py        # structlog + stdlib logging setup
│   │
│   ├── db/
│   │   ├── base.py              # Declarative Base + shared column helpers
│   │   ├── engine.py, session.py  # SQLAlchemy engine/session factory
│   │   ├── models/              # One ORM model per file (manga, genres, sources,
│   │   │                          manga_external_ratings, users)
│   │   └── repositories/        # Data-access functions, one module per model
│   │
│   └── ingestion/
│       ├── base.py              # BaseExtractor ABC, NormalizedMangaRecord
│       ├── anilist.py           # AniList extractor — concurrent id_in chunk fetch
│       ├── registry.py          # source name -> extractor/default-weight mapping
│       ├── loader.py            # persists NormalizedMangaRecords to the database
│       └── runner.py            # seeds sources, batches extraction, calls loader
│
├── alembic/                     # Migrations (`uv run alembic revision --autogenerate`)
├── tests/                       # pytest, mirrors src/ layout
│
├── .env.example
├── Dockerfile
├── Makefile
├── pyproject.toml               # All deps and tool config live here
├── railway.toml                 # Railway deploy config
└── uv.lock                      # Commit this — pins exact versions
```

Not built yet: the FastAPI `api`/`services` layer (routers, business logic — no HTTP,
no SQL strings) and the recommendation engine itself.

## Environment variable reference

| Variable | Required | Description |
|---|---|---|
| `DB_URL` | recommended | Direct Supabase connection — use for local dev and migrations |
| `DB_URL_POOLED` | recommended | Supabase transaction pooler — use in production |
| `APP_ENV` | — | `development` or `production` (default `development`) |
| `APP_DEBUG` | — | `true` enables verbose errors (default `true`) |
| `API_HOST` | — | Bind host — `0.0.0.0` for Docker/Railway (default `0.0.0.0`) |
| `API_PORT` | — | Bind port (default `8000`) |
| `LOGGING_LEVEL` | — | Log level, e.g. `INFO`/`DEBUG` (default `INFO`) |
| `ANILIST_REQUESTS_PER_MINUTE` | — | AniList rate limit budget (default `30`) |
| `ANILIST_CHUNK_SIZE` | — | IDs per `id_in` request (default `50`, AniList's max) |
| `ANILIST_MIN_ID` | — | Lowest manga ID to fetch (default `30001` — below this is all anime) |
| `ANILIST_MAX_ID` | — | Highest manga ID to fetch (default: resolved live from AniList) |
| `INGESTION_BATCH_SIZE` | — | Records per `load_batch` transaction (default `50`) |

Every variable has a fallback in `config.py`, so none are strictly required to boot —
`DB_URL`/`DB_URL_POOLED` are marked "recommended" because the fallback points at a
placeholder local Postgres, not a real database. `SECRET_KEY`/`CORS_ORIGINS` aren't
listed because auth and CORS aren't implemented yet.
