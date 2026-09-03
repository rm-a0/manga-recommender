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

Both CLI commands are wired up. `app` starts uvicorn on `API_HOST:API_PORT`.

```bash
uv run python -m manga_recommender ingest --source anilist    # run ingestion
uv run python -m manga_recommender ingest --source kaggle_mal # the other source
uv run python -m manga_recommender app                        # serve the API
```

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness. Touches no dependency |
| `GET /ready` | Readiness. One entry per checked dependency |
| `GET /manga` | One page of manga summaries (`limit`, `offset`) |
| `GET /manga/{manga_id}` | One manga in full, or 404 |
| `GET /authors` | One page of author summaries (`limit`, `offset`) |
| `GET /authors/{author_id}` | One author in full, or 404 |
| `GET /authors/{author_id}/manga` | One page of that author's manga (`limit`, `offset`) |
| `GET /tags` | One page of tag summaries (`limit`, `offset`) |
| `GET /tags/{tag_id}` | One tag in full, or 404 |
| `GET /tags/{tag_id}/manga` | One page of the manga carrying that tag (`limit`, `offset`) |

Interactive docs are at `/docs` once the server is up.

## Database migrations

Migrations use [Alembic](https://alembic.sqlalchemy.org/). Always run them against
the **direct connection** (`DB_URL`), not the pooled URL.

```bash
uv run alembic upgrade head                                        # apply all pending
uv run alembic revision --autogenerate -m "describe what changed"  # after model changes
uv run alembic current                                             # check current state
uv run alembic downgrade -1                                        # roll back one
```

> Migrations run automatically on every deploy (see `.github/workflows/cd.yml`).
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
no data files. Production still deploys against Supabase (via Azure Container
Apps); the
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
import its (not-yet-existing) `manga_recommender.api.main:app` - expected until
that module exists.

## Tests and Postgres

The test suite doesn't use the `docker-compose.yml` Postgres at all - `tests/
conftest.py` spins up its own ephemeral Postgres container via
[testcontainers](https://testcontainers-python.readthedocs.io/) once per test
session, forces `DB_URL` to point at it (overriding whatever `.env` says), and
runs Alembic migrations automatically before any test runs. Just `uv run
pytest` / `make test` - no `make db-up` step needed, and nothing ever touches
Supabase or the local dev database. Requires Docker to be running locally.

## Deployment (Azure Container Apps)

The API runs on Azure Container Apps. Postgres stays on Supabase. Every push to
`main` deploys automatically through `.github/workflows/cd.yml`:

```
build image -> push to GHCR -> alembic upgrade head -> az containerapp update -> smoke test /ready
```

Migrations run from the GitHub Actions runner, not from the container start
command. The app scales to zero, so replicas start unpredictably and several
could otherwise run Alembic at the same time.

### Supabase connection strings

Use the **session pooler**: host `aws-0-<region>.pooler.supabase.com`, port
`5432`, user `postgres.<project-ref>`.

- The **direct** connection (`db.<project-ref>.supabase.co`) is IPv6-only.
  Container Apps has no outbound IPv6 and fails with `Cannot assign requested
  address`.
- The **transaction pooler** (port `6543`) cannot run migrations. Alembic needs
  DDL and session-level locks.

The pooler user needs the project ref appended. Copying only the host across from
the direct connection string does not work.

### Required GitHub configuration

Under Settings -> Environments -> `production`:

| Kind | Name | Purpose |
|------|------|---------|
| secret | `AZURE_CLIENT_ID` | App registration used by `azure/login` |
| secret | `AZURE_TENANT_ID` | Entra tenant |
| secret | `AZURE_SUBSCRIPTION_ID` | Target subscription |
| secret | `DB_URL` | Session pooler URL, for the migration step |
| variable | `APP_FQDN` | Container app hostname, for the smoke test |

Azure authentication uses OIDC federated credentials, so no client secret is
stored. The credential subject is
`repo:rm-a0/manga-recommender:environment:production` and must match the job's
`environment: name`.

### Azure resources

| Resource | Name |
|----------|------|
| Resource group | `rg-manga-rec` |
| Container apps environment | `cae-manga-rec` |
| Container app | `manga-rec-api` |
| Region | `germanywestcentral` |

An allowed-locations policy on the subscription fixes the region. Scale is min 0
/ max 2 replicas, so the first request after an idle period pays a cold start.

The image at `ghcr.io/rm-a0/manga-recommender` must stay **public**. The
container app pulls anonymously, with no registry credentials configured.

## Project structure

```
manga-recommender/
│
├── src/manga_recommender/
│   ├── __main__.py             # `python -m manga_recommender` shim -> cli.main
│   │
│   ├── api/                    # HTTP layer - the only place FastAPI is imported
│   │   ├── main.py              # create_app() + the ASGI `app` object
│   │   ├── dependencies.py      # HTTP-shaped Depends (DbSession, Pagination)
│   │   └── routes/              # One module per resource; HTTP only, no SQL
│   │                              (probes, manga, authors)
│   │
│   ├── cli/
│   │   └── main.py              # Typer app: `ingest`, `app`
│   │
│   ├── core/                   # Cross-cutting infrastructure
│   │   ├── config.py            # Settings loaded from .env via pydantic-settings
│   │   └── logging_config.py    # structlog + stdlib logging setup
│   │
│   ├── db/
│   │   ├── base.py              # Declarative Base + shared column helpers
│   │   ├── engine.py            # Cached SQLAlchemy engine
│   │   ├── session.py           # Session factory; session_scope + get_db
│   │   ├── models/              # One ORM model per file (manga, tags, authors,
│   │   │                          sources, manga_external_ratings, users)
│   │   └── repositories/        # Data-access functions, one module per model
│   │
│   ├── schemas/                # Pydantic request/response models, one per resource
│   │                              (common Page[T], probes, manga, authors, tags)
│   ├── services/               # Business logic - no HTTP, no SQL strings
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
├── .github/workflows/           # ci.yml gates merges, cd.yml deploys main
└── uv.lock                      # Commit this — pins exact versions
```

**Layering rule.** Each layer talks only to the one below it: `routes` parse HTTP and
call a service, never a repository; `services` hold business logic and never import
FastAPI; `repositories` are the only place SQL lives. Definitions live with the layer they
belong to — `get_db` sits in `db/session.py` beside `session_scope`, and `api/` holds
only the adapter to HTTP.

The manga, authors and tags resources are live end to end — route, service,
repository. Schemas name the payload shape rather than the endpoint: `MangaSummary` for a list
item, `MangaDetail` for one resource, with `Page[T]` in `schemas/common.py` wrapping
any paginated list. A third form, `<Parent><Child>`, appears only where the link
between two resources carries data of its own — `MangaTag` holds the `rank` and
`is_spoiler` that describe the manga-tag link rather than the tag itself.

Two rules keep the schema modules importable in any order:

- **Embedding points from detail to summary, never the reverse**, so a module never
  has to import the module that imports it. A summary holds only cheap fields,
  because one page can carry up to a hundred of them.
- **A relationship unbounded in one direction gets its own endpoint**, not a field.
  An author's manga is `GET /authors/{author_id}/manga`; `AuthorDetail` carries only
  `manga_count`, which costs one extra query and so stays out of the list response.

That sub-collection answers `200` with an empty page for an author ID that matches
no row, where `GET /authors/{author_id}` answers `404` — a collection that is empty
is not a collection that is missing. `GET /tags/{tag_id}/manga` follows the same
rule.

Not built yet: the recommendation engine itself. Domain
exceptions map to HTTP inside each route for now; a shared `api/errors.py` is worth
adding once several routes raise the same failure.

## Environment variable reference

| Variable | Required | Description |
|---|---|---|
| `DB_URL` | recommended | Direct or **session pooler** — always used by migrations and ingestion |
| `DB_URL_POOLED` | production | Transaction pooler — used by the API when `DB_USE_POOLED=true` |
| `DB_USE_POOLED` | — | `true` routes the API through `DB_URL_POOLED` (default `false`) |
| `DB_POOL_SIZE` | — | SQLAlchemy pool size (default `5`) |
| `DB_MAX_OVERFLOW` | — | Connections allowed beyond the pool (default `10`) |
| `DB_STATEMENT_TIMEOUT` | — | Milliseconds; unset inherits the server default, `0` disables it |
| `APP_ENV` | — | `development` or `production` (default `development`) |
| `APP_DEBUG` | — | `true` enables verbose errors (default `true`) |
| `API_HOST` | — | Bind host — `0.0.0.0` for Docker/Container Apps (default `0.0.0.0`) |
| `API_PORT` | — | Bind port (default `8000`) |
| `LOGGING_LEVEL` | — | Log level, e.g. `INFO`/`DEBUG` (default `INFO`) |
| `ANILIST_REQUESTS_PER_MINUTE` | — | AniList rate limit budget (default `30`) |
| `ANILIST_CHUNK_SIZE` | — | IDs per `id_in` request (default `50`, AniList's max) |
| `ANILIST_MIN_ID` | — | Lowest manga ID to fetch (default `30001` — below this is all anime) |
| `ANILIST_MAX_ID` | — | Highest manga ID to fetch (default: resolved live from AniList) |
| `INGESTION_BATCH_SIZE` | — | Records per `load_batch` transaction (default `50`) |
| `KAGGLE_MAL_PATH` | — | Path to the Kaggle MAL CSV (default `data/kaggle_mal_2026.csv`) |

Every variable has a fallback in `core/config.py`, so none are strictly required to boot —
`DB_URL` is marked "recommended" because the fallback points at a placeholder local
Postgres, not a real database. `DB_URL_POOLED` has no fallback: setting
`DB_USE_POOLED=true` without it fails at startup rather than silently connecting
direct. `SECRET_KEY`/`CORS_ORIGINS` aren't listed because auth and CORS aren't
implemented yet.
