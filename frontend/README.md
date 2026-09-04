# MangaRec frontend

Next.js 16 (App Router) + TypeScript + Tailwind v4. Reads the FastAPI catalogue in
`backend/` over HTTP; the browser never calls that API directly, so its missing CORS
configuration never matters.

## Run it

The API and a seeded database must be up first — from the repo root:

```bash
make db-up
DB_URL=postgresql://postgres:password@localhost:5433/mangarec \
  uv run python -m manga_recommender ingest --source kaggle_mal   # once, ~1 min
DB_URL=postgresql://postgres:password@localhost:5433/mangarec \
  uv run python -m manga_recommender app                          # API on :8000
```

Then here:

```bash
npm install
npm run dev          # http://localhost:3000
```

`API_BASE_URL` defaults to `http://localhost:8000`; set it to point elsewhere.

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
