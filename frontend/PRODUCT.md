# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Next.js (App Router) + TypeScript + Tailwind CSS, in `frontend/` at the repo root.

Chosen by the user from a recommendation. The deciding constraint: `backend/manga_recommender/api/main.py`
registers no `CORSMiddleware`, and AGENTS.md reserves all `backend/` code for the user
to hand-write. Server-side rendering means the browser only ever talks to Next, so the
missing CORS configuration never becomes a blocker. Secondary reasons: the API's flat
query-parameter surface maps directly onto App Router `searchParams`, giving shareable
filter URLs for free; `next/image` handles cover art that arrives unsized from two
third-party CDNs; and streaming covers the scale-to-zero cold start.

No deployment work in this scope — the app runs locally against the API. Hosting is
undecided and nothing written should constrain that choice.

## Users

Manga readers deciding what to read next, including the author of the project. They
arrive with something in mind — a title they just finished, a handful of series they
liked, eventually an imported MAL list — and want candidates they have not already read.

Secondary: people browsing the catalogue directly, by tag, author, or title search.

## Product Purpose

Recommend manga. The catalogue exists to support that, not the other way around. Success
is a reader leaving with a title they want to read and would not have found alone.

Open source. Not a commercial product and not for sale, so there is no signup, no
pricing, no conversion path, and no persuasion layer.

## Positioning

Multi-strategy recommendation over one catalogue. Existing sites (MAL, AniList) are
catalogues with a single fixed recommendation mechanism attached. The intended mechanism
here is that the reader picks — or composes — the strategy: prior reading history,
semantic similarity over tags and descriptions, collaborative signal from other readers,
or a custom blend with tags excluded and specific likes and dislikes weighted.

None of this is built yet. The engine does not exist.

## Operating Context

The reader is at a keyboard, mid-decision, usually referencing titles they already know.
Reference titles are typed by name, so title search is on the critical path of the
primary flow, not a secondary feature.

## Capabilities and Constraints

Working today, via the existing FastAPI JSON API:

- `GET /manga` — paginated list. Filters: `q` (title, min 2 chars), `status[]`,
  `include_tag[]` / `exclude_tag[]` (by name, max 10, `tag_match=any|all`),
  `published_from` / `published_to`. Sort: `title` or `published_date`, `asc|desc`.
  `limit` max 100, offset pagination, `total` returned.
- `GET /manga/{id}` — adds `published_date`, `description`, and `tags` with `rank` and
  `is_spoiler`.
- `GET /tags`, `GET /tags/{id}`, `GET /tags/{id}/manga`
- `GET /authors`, `GET /authors/{id}`, `GET /authors/{id}/manga`
- `GET /health`, `GET /ready`

Not available, and must not be faked:

- Any recommendation endpoint. No similarity, no ranking, no personalisation.
- Sorting by score, popularity, or relevance — `MangaSort` has these commented out.
- A `q` filter on `/authors`. Author lookup by name is not possible.
- English titles. Search matches romaji only, so `attack on titan` returns nothing
  while `shingeki no kyojin` works. Users must be told this rather than left guessing.
- User accounts, lists, or persistence of any kind. The `users` table is unused.

Constraints that shape the interface:

- **Cover art is small.** The stored `image_url` measures ~225x320, sharp only to about
  112 CSS px on a 2x display. MAL serves a larger variant by inserting `l` before `.jpg`
  (verified 8/8 on sample), typically ~400x600 but capped by the original upload — two
  of eight reached only 276x393 and 285x450. Practical ceiling is ~200 px sharp,
  worst case ~140 px. Large editorial cover treatments are not possible.
- **~30% of manga have no description** (24,400 of 82,629 in the local dataset).
  The detail page must read as complete without one.
- **Title search is a sequential scan** (`ILIKE '%term%'`, no index), so it needs
  debouncing rather than per-keystroke queries.
- **Cold start.** The API scales to zero, so the first request after idle is slow.
  Shell and skeletons must paint before data arrives.
- **Boundary.** AGENTS.md reserves recommendation logic for `backend/`. The frontend
  composes existing endpoint calls and renders results in the order returned. It does
  not score, rank, or weight anything client-side.

## Brand Commitments

Name is display-only and must not affect URLs, package names, repository name, or any
identifier in code — those stay `manga-recommender` / `MangaRec`.

Rejected direction: bookshop and library metaphors. They describe a catalogue, and this
is a recommender.

Display name: OPEN. Candidates are a single kanji mark paired with the MangaRec
wordmark. Preference is for something recommendation-related, simple and clean, and
explicitly not corny.

## Evidence on Hand

- Local Docker Postgres, seeded from `data/kaggle_mal_2026.csv`: 82,629 manga (all with
  cover URLs), 58,229 descriptions, 79 tags, 34,835 authors. Real content to design
  against — no placeholder text needed.
- A second source, AniList, exists in the ingestion pipeline but is not in the local
  dataset. Its covers come from a different CDN with a different URL shape.
- No users, no usage data, no reviews, no testimonials. None may be invented.

## Product Principles

1. **The recommender is the product.** The catalogue is how the reader specifies what
   they want, and where results land. It is not the destination.
2. **Never claim a recommendation the engine did not make.** With no engine, the
   interface says so plainly rather than dressing up a filtered query as insight.
3. **Design for the strategy list being long.** Every future strategy shares one input
   (a set of reference titles) and one output (a set of manga). Build that shape now so
   later strategies are additions, not redesigns.
4. **Placeholders must leave no scar.** Anything standing in for unbuilt work is removed
   by deletion, never by rewriting around it, and the design should improve when the
   real thing arrives.
5. **State the limits in the interface.** Romaji-only search, missing descriptions and
   an empty result set are told to the reader directly, not hidden behind a spinner or a
   blank grid.

## Accessibility & Inclusion

No project-specific standard established. Baseline expectation: keyboard operable,
visible focus, real semantics, and text alternatives for cover art — cover images carry
the title, so they are never the only label.
