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
uv run python -m manga_recommender ingest --source anilist    # run ingestion
uv run python -m manga_recommender ingest --source kaggle_mal # the other source
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

A **one-shot offline job**, not triggered by the API. Two sources feed the same
`NormalizedMangaRecord` shape and the same loader.

| Source | Where from | Full run |
|---|---|---|
| `anilist` | AniList GraphQL API, concurrent rate-limited `id_in` chunks | ~2.5 hours |
| `kaggle_mal` | Local CSV of the Kaggle MAL 2026 dataset | minutes |

AniList is walked by raw ID space rather than paginated, since its page-based
pagination caps out at 5,000 results.

```bash
uv sync --group pipeline                                      # install pipeline extras
uv run python -m manga_recommender ingest --source kaggle_mal
uv run python -m manga_recommender ingest --source anilist

# Small test run, capped to a handful of chunks instead of the whole catalogue
ANILIST_MAX_ID=30201 uv run python -m manga_recommender ingest --source anilist
```

> **Order matters.** Manga metadata is upserted with `COALESCE`, so the source
> that runs last wins every field it has a value for. Run `kaggle_mal` first and
> `anilist` second, so the richer AniList titles and descriptions end up on top.
> Re-running `kaggle_mal` against a populated database overwrites them.

Fetching dominates the AniList run (bounded by its rate limit); a full pass took
~2h30m for the ~186k-ID space. Loading — manga, genre, author and rating writes,
all bulk-upserted — takes roughly ~20-25 minutes of that.

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
no data files. Production still deploys against Supabase (via Railway); the
container itself is stateless.

```bash
docker build -t mangarec .
docker run --env-file .env -p 8000:8000 mangarec
```

## Local Docker Compose (app + Postgres)

`docker-compose.yml` runs the app alongside a local Postgres (database
`mangarec`) - an alternative to Supabase for local dev/offline use.

```bash
make stack    # start the full stack: the app (built from the Dockerfile) + Postgres
make db-up    # start only Postgres (postgres:16, host port 5433) - for local dev
make down     # stop everything
```

> Postgres is on host port 5433, not the default 5432, to avoid clashing with
> a natively-installed Postgres if one is already running. Inside the compose
> network the app reaches it at `postgres:5432` instead.

The `app` service builds from the same Dockerfile as production and reads
`.env` (if present), with `DB_URL` overridden to point at the compose
`postgres` service. Its `CMD` runs `uvicorn` directly against the FastAPI app -
ingestion is a separate, offline job (see below) and is never run in this
container, so there's no shared-entrypoint reason to route the container
through the CLI. Since the FastAPI app itself isn't built yet (see above),
`make stack` will start Postgres fine but the `app` container currently fails to
import its (not-yet-existing) `manga_recommender.main:app` - expected until
that module exists.

## Tests and Postgres

The test suite doesn't use the `docker-compose.yml` Postgres at all - `tests/
conftest.py` spins up its own ephemeral Postgres container via
[testcontainers](https://testcontainers-python.readthedocs.io/) once per test
session, forces `DB_URL` to point at it (overriding whatever `.env` says), and
runs Alembic migrations automatically before any test runs. Just `uv run
pytest` / `make test` - no `make db-up` step needed, and nothing ever touches
Supabase or the local dev database. Requires Docker to be running locally.

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
│   │   ├── models/              # One ORM model per file (manga, genres, authors,
│   │   │                          sources, manga_external_ratings, users)
│   │   └── repositories/        # Data-access functions, one module per model
│   │
│   └── ingestion/
│       ├── base.py              # BaseExtractor ABC, NormalizedMangaRecord
│       ├── extractors/          # anilist.py (concurrent id_in chunk fetch),
│       │                          kaggle_mal.py (local CSV)
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
| `KAGGLE_MAL_PATH` | — | Path to the Kaggle MAL CSV (default `data/kaggle_mal_2026.csv`) |

Every variable has a fallback in `config.py`, so none are strictly required to boot —
`DB_URL`/`DB_URL_POOLED` are marked "recommended" because the fallback points at a
placeholder local Postgres, not a real database. `SECRET_KEY`/`CORS_ORIGINS` aren't
listed because auth and CORS aren't implemented yet.
