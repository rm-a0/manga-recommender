# MangaRec frontend

Next.js 16 (App Router) + TypeScript + Tailwind v4. Reads the FastAPI catalogue in
`backend/` over HTTP; the browser never calls that API directly, so its missing CORS
configuration never matters.

## Run it

`make ui` (from the repo root) serves the UI on `http://localhost:3000`. It installs
the npm dependencies on the first run.

### Against the local API

The API and a seeded database must be up first — from the repo root:

```bash
make db-up
DB_URL=postgresql://postgres:password@localhost:5433/mangarec \
  uv run python -m manga_recommender ingest --source kaggle_mal   # once, ~1 min
DB_URL=postgresql://postgres:password@localhost:5433/mangarec \
  uv run python -m manga_recommender app                          # API on :8000

make ui                                                           # UI on :3000
```

### Against a deployed API

Needs nothing running locally — pass the host and skip the three commands above:

```bash
make ui api=https://your-deployed-api
```

`api=` sets `API_BASE_URL` for that run only. Left off, the UI reads `API_BASE_URL`
from `frontend/.env.local` if that file exists, and otherwise defaults to
`http://localhost:8000`. Put the deployed host in `.env.local` (gitignored) to make it
the default and then just run `make ui`.

## Layout

| Path | What |
|---|---|
| `app/` | Routes. `/` recommender, `/browse` catalogue, `/manga/[id]`, `/tags`, `/authors/[id]` |
| `app/api/search/` | Route handler the survey field calls, so the browser never hits the catalogue API |
| `components/` | View components. `HallGrid` is the system's atom |
| `lib/api.ts` | Typed client, one function per endpoint |
| `lib/types.ts` | Mirrors `backend/manga_recommender/schemas/*.py` — the backend is the authority |
| `lib/routes.ts` | The reading routes. One is live; the rest are recorded, not faked |
| `lib/covers.ts` | Cover URL upgrade. Delete it if a larger URL is ever stored at ingest |
| `lib/ordering.ts` | The orderings the hall offers, and how a heading names each one |
| `lib/score.ts` | Reads the metrics row out of ten, and sets vote counts |
| `lib/explicit.ts` | Which codes are explicit. Delete it if the API ever says so itself |

## Design

`DESIGN.md` is the design system, recorded from the built code. `PRODUCT.md` is product
truth. `.impeccable/surfaces/app.md` holds the direction contract.

Two rules matter more than the rest:

1. **A listing may rank, and must say what ranked it.** The API orders by the catalogue's
   own weighted score and by vote count, so every listing names the field that ordered
   it. What no listing may suggest is that it was ordered by how well a title answers
   what the reader ringed — that needs the recommendation engine, which does not exist.
2. **No recommendation logic here.** Per the repo's `AGENTS.md`, that belongs in
   `backend/`. This app asks the API to order a listing and renders what comes back, in
   the order it comes back. It scores and weighs nothing itself.

### The explicit codes

`lib/explicit.ts` is a stopgap. Neither `manga` nor `tags` carries a content rating, so
which codes are explicit is written down in the frontend. Two lists, because they answer
different questions: `SEALED_WORK_TAGS` feeds `exclude_tag`, which the API caps at ten
values, and `SEALED_TAGS` hides codes from pickers, which has no cap. An `is_adult`
column set at ingest and surfaced on the tag and manga models would replace the whole
file with one boolean — worth doing before AniList ingestion grows the vocabulary.

## Checks

```bash
npx tsc --noEmit
npx eslint .
npm run build
```
