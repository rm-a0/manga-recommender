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

## Design

`DESIGN.md` is the design system, recorded from the built code. `PRODUCT.md` is product
truth. `.impeccable/surfaces/app.md` holds the direction contract.

Two rules matter more than the rest:

1. **Nothing may imply a ranking.** The API has no score, popularity or relevance
   ordering. Every listing names the field that ordered it; table codes (`A-01`) are
   coordinates in the current listing, never ranks.
2. **No recommendation logic here.** Per the repo's `AGENTS.md`, that belongs in
   `backend/`. This app composes existing endpoint calls and renders what comes back, in
   the order it comes back.

## Checks

```bash
npx tsc --noEmit
npx eslint .
npm run build
```
