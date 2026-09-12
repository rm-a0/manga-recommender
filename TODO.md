# TODO

Planned work, not yet scheduled.

## Ingestion

- Per-source ingest mode flags (`--create-only` / `--update-only`), so a second
  source can refresh ratings without overwriting the first one's metadata.
  Depends on splitting `ingestion/` into catalogue vs. user-signal submodules.
- Bound the 429 retry depth. It resets `attempt` to 1 and recurses.
- Backpressure on the fetch side. `_stream` schedules every chunk at once, and
  only the consumer is throttled.
- Clean descriptions at ingest. Landed 2026-09-12 as `_clean_description` in
  each extractor. Kaggle MAL: unescape twice, drop every `[Written by ...]`
  credit and `(Source ...)` attribution (the separator is written as ":", ";",
  "-" or a space, and the 1000-character cap can cut the closing bracket), cut a
  trailing `Included one-shots` list, then tidy the whitespace and read a
  placeholder as NULL. Measured over 58,401 synopses: no trailer, credit,
  entity or list survives, 474 rows become NULL (433 of them held only a
  one-shot list), and 52,027 still clear the 100-character export gate.
  AniList: `<br>` becomes a line break before the other tags go, and the
  unescape runs after that, so an escaped bracket cannot turn into a tag.
  Spoiler markers go, the text inside stays. Paragraph breaks survive on both
  sides, because the detail page shows this text.
  Needs a re-ingest to reach the stored rows, then `export` and `embed` again.
  Every cleaned row changes its text hash, so the embed stage re-encodes it.
- Fetch AniList's `english` title, plus structured
  `name { first last native }` for staff. Both need a re-ingest. `native` and
  `synonyms` are not stored (see English titles under Database).

## Database

- Make the highest-votes canonical rule hold across batches, not only within
  one. Needs an arbitration column on `manga` and a `WHERE` on the conflict
  update.
- Reconcile records that have no `mal_id` against the same series from another
  source. Measure how many AniList entries lack one before choosing an approach.
- Prune link rows a source no longer writes. Both link tables are insert-only
  and neither records which source added a row.
- Add `role` to `manga_authors` once something needs Story separate from Art.
- Revisit `delete_orphaned_manga`'s predicate if a source ever supplies
  descriptions without ratings.
- Explicit content flag on `manga`. The catalogue carries adult titles and nothing
  marks them, so every listing and every recommendation can return one. Needs a
  column on `manga`, both extractors writing it, and a decision on the API surface:
  a default-off `include_explicit` query parameter is the smallest shape, but the
  filter has to reach the recommendation routes too, not only `GET /manga` — a
  vector search that ignores it leaks exactly what the flag exists to hide. Source
  signal differs: AniList gives a boolean `isAdult`, Kaggle MAL gives the `Hentai`
  and `Erotica` genres, so `_to_record` derives the same flag two ways.
  Landed 2026-09-12 as a flag on `tags`, not on `manga`: AniList sets `isAdult`
  per tag, Kaggle marks the `Hentai` and `Erotica` genres, and the tag upsert
  keeps the union, so source order cannot lose the flag. Still open: a manga is
  explicit when any of its tags is, and nothing computes that yet.
  `MangaSummary` carries no tags, so a listing cannot hide an adult title, and
  the client must not be the one to decide. Needs a derived `is_explicit` on
  `MangaSummary` and `MangaDetail`, plus a default-off `include_explicit` that
  filters in SQL (`NOT EXISTS` over the explicit tags) on `GET /manga` and on
  every recommendation route.
- Type column on `manga` — manga, manhwa, manhua, novel, one-shot, doujinshi.
  Both sources carry it (`format` on AniList, `type` on Kaggle MAL) and neither is
  read. An enum like `manga_status`, so it needs a migration and a re-ingest.
  Earns a repeatable `type` filter on `GET /manga`, and a reader asking for manhwa
  is a common enough ask that a tag cannot serve it.
  Landed 2026-09-12: `manga.type`, both extractors, and `MangaFilters.types`.
  `Novel` folds into `light_novel` on purpose, and AniList needs
  `countryOfOrigin` as well as `format` to tell a manhwa from a manga. Still
  open: no request reaches the filter. `MangaListParams` has no `type` field and
  `_to_filters` never fills `types`, so the filter is unreachable. `MangaSummary`
  also omits `type`, so a list cannot show the badge it would filter on.
- Store English titles. `data/kaggle_mal_2026.csv` already carries `title_english`
  and `title_japanese`, and `_to_record` reads neither, so search only matches the
  romaji: `q=attack on titan` finds nothing, `q=shingeki no kyojin` finds it. One
  column, one line in `kaggle_mal.py`, then re-run `ingest --source kaggle_mal`.
  AniList needs `title { romaji english }` in the query and a full re-ingest.
  Deferred to the same PR as the `published_date` narrowing below, to spend one
  migration and one re-ingest on both. Not a storage question: ~30 bytes a row is
  ~6 MB at full catalogue size.
  Decided 2026-09-11: store only the English title, as one column. No Japanese
  titles: a reader rarely types kana, and the trigram index does not help across
  scripts, so the column would serve display only. No `synonyms` and no
  `manga_titles` table: a one-to-many table and an `EXISTS` on every search cost
  too much for alternate spellings. The English title covers the main search
  gap, and trigram search covers near-miss spellings.
- Narrow `manga.published_date` from `DateTime(timezone=True)` to `Date`. Neither
  source carries a time: Kaggle gives `YYYY-MM-DD` and AniList gives
  `{year, month, day}`, so both extractors build a midnight datetime that means
  nothing. Saves 4 bytes a row, drops the timezone question, and lets the API's
  `published_from`/`published_to` filters compare date to date instead of a naive
  datetime against a tz-aware column. `ALTER COLUMN ... TYPE date` casts in place,
  so no re-ingest. Touches the model, `MangaUpsertValues`, `MangaDetail`, both
  extractors and `ingestion/base.py`, plus ~25 test references.
- Canonical display names for tags. `normalize_tag_name` folds case, accents and
  punctuation, so the stored `name` is whichever spelling a source wrote first
  ("Sci-Fi" vs "Sci Fi"). Needs a display map keyed on `normalized_name`, applied
  at upsert. The vocabulary is closed (~150 tags), so a backfill fixes existing
  rows — no re-ingest.
- Better display names for authors. `_is_better_display_name` only prefers a
  spelling without a comma, so casing and accents fall to whichever arrived first
  ("Kohei" beating "Kōhei", "CLAMP" flattened by an ALL-CAPS-first source). Needs
  richer rules, or `Source.weight` as the tiebreak. Needs a re-ingest either way:
  only the winning spelling is stored, so the alternatives are already gone.
- Migrate DB from Supabase to Aiven, delete all alembic versions before seeding
  and generate initial one from scratch.

## API

- Trigram search behind the existing `q`. Title search is `ILIKE '%term%'`, which
  no btree index can serve, so every search is a sequential scan. `CREATE EXTENSION
  pg_trgm` plus a GIN index on `title gin_trgm_ops` makes the same query use an
  index — no API or query change. Only ranking needs new SQL: `similarity()` in the
  ORDER BY, which is also what unlocks `MangaSort.RELEVANCE`.
- Accent folding in search. `q=Kohei` does not match `Kōhei`. Needs `unaccent`
  and a normalized title, either as a functional index or a `normalized_title`
  column written at ingest — the same shape as the normalized score column below.
- A `q` filter on `GET /authors`. An author picker needs name search, and the
  table is large enough that the frontend cannot hold it. One `ILIKE` on
  `Author.name`. `GET /tags` does not need one: the vocabulary is ~150 rows, so
  the frontend fetches it once and filters locally.
- Decide the fate of `GET /tags/{id}/manga` and `GET /authors/{id}/manga`.
  `GET /manga?include_tag=...` already does the tag case with every filter and
  sort, so the sub-route is a second, weaker parameter surface that will drift.
  Either drop it, or keep it and never grow filters on it. Blocked on the
  frontend: the sub-route takes a tag ID, the `/manga` filter takes a tag name.
- Sorting by score. `raw_score` sits on `manga_external_ratings` against a
  per-source `raw_scale_max`, so ordering by it means normalizing and aggregating
  per row. Needs a normalized score column on `manga`, written at ingest —
  the same shape as the arbitration column the database section already wants.
- A manga with no embedding needs its own answer on the recommendation routes.
  A large minority of the catalogue is outside the `export` gate — the 37% figure
  came from the Kaggle seed and no longer holds, so re-derive it from
  `count(*) FROM manga` against 93,514 exported. "More like this" on an
  unexported manga is not an empty result — it is "no usable synopsis, here is
  shared tags instead". Decide the response shape before the semantic route
  ships, so the frontend can render a fallback rather than an apology.
- An index on `manga.title`. Every page already pays a full sort for
  `ORDER BY title OFFSET n`.

## Not built yet

- The recommendation engine, including semantic search over descriptions.

## Pipeline

Stages run in order: `fill` -> `export` -> `embed` -> `index` -> `train`.
Registry order is the run order, so `--stage` accepts any order.

- `fill`: post-ingestion in-DB work. Bayesian metrics are done. Still to do:
  canonical arbitration, normalized title, tag display names, orphan prune
  (move it out of `ingestion/runner.py`).
- `export`: DB -> Parquet snapshot. Built. Everything downstream reads the
  snapshot, not the live database. Read-only: it writes no rows.
  Owns row selection and field shape; it does not compose model input text.
  Emits structured columns (id, title, description, tags as `list<string>`), so
  changing the embedding template is an `embed` re-run with no DB round trip.
  Gate: only manga whose description is at least 100 characters after trimming.
  That was 52,236 of the 82,629 rows in the Kaggle seed (63%). The catalogue has
  grown since, and the first full run on 2026-09-08 exported 93,514 rows — the
  count confirmed against both the database and the written snapshot, every id
  distinct. Re-measure the excluded tail before quoting a percentage against it.
  No title-plus-tags fallback for the rest — the tag vocabulary is closed
  (79 tags), so those rows would produce near-identical vectors with cosine near
  1, which returns arbitrary neighbours and degrades the HNSW graph for the good
  rows as well.
  The short tail is mostly tables of contents listing included one-shots, plus
  literal `None.`; it is not thin synopsis text. Cost was roughly 6,000 genuine
  one-line synopses excluded on the Kaggle seed, accepted because length cannot
  separate them from the list-shaped noise; the figure is stale for the larger
  catalogue and was never re-derived. The rows left out are exactly what the
  live shared-tags route already serves. Adding rows back later is an `embed` +
  `index` re-run with no schema change; removing them after readers have seen
  results is not.
  Write artifacts to `data/artifacts/`, not `data/` itself — `data/` holds the
  44 MB hand-downloaded Kaggle CSV, and generated files must stay separately
  disposable. All of `data/` is already gitignored.
- `embed`: Parquet -> `.npz`. No DB writes. Import `sentence_transformers`
  inside the stage, so the registry can import every stage at module scope.
  Built.
  Change the text template from `title desc tags` to `desc tags`, and drop the
  title. Measured on 2,000 sampled rows with bge-small (2026-09-11). The model
  weights the start of the text: the same field moves the vector 2.7x more at
  the start than at the end for the title (1 - cos 0.059 vs 0.022), and 1.6x
  more for tags (0.060 vs 0.037). Two random manga already sit at cos 0.594, so
  a 0.06 shift is ~15% of the usable range. Romaji titles carry no meaning for
  an English model, only spelling overlap, so title-first gives franchise and
  lookalike neighbours (One Piece -> "CHIN PIECE", 0.815). Neighbours that share
  a title word: 4.3% with the title first, 2.0% without it, and higher on the
  full catalogue, where franchises are dense. Truncation does not decide the
  order: 99.5% of rows fit in 512 tokens (median 130, p99 407), and the tail of
  the other 472 is mostly chapter lists. The order changes results a lot (top-10
  overlap with the current template: 37% for `desc tags`), but no measurement
  says which is better yet. Before locking the template, score each variant by
  recall@10 against MAL user recommendations (Jikan
  `/manga/{id}/recommendations`) on a few hundred seeds. Tags stay in the text
  for free-text semantic search. A re-rank of the top 100-200 by
  `cos + λ·tag_overlap` can come later, but it only reorders vector candidates.
  Revisit the title once English titles are stored.
- `index`: `.npz` -> `manga_embeddings`, then build HNSW. Load the rows before
  the HNSW index exists, as pgvector recommends: drop the index, bulk insert,
  create it again.
- `train`: needs user-item data first. Blocked.
- A failed stage halts the run. Unlike sources, which are independent and
  log-and-continue. `depends_on` is not needed: the graph is a path, and list
  order already encodes it.
- Each stage checks its own input artifact instead. Staleness is a fact about
  files, not about the graph.

## ML / NLP

Checkpoints, shortest form. Expand when each is started.

- Content embeddings. Description + tags -> `halfvec(384)`, HNSW. See `embed`.
  Powers "more like this" and semantic search.
- User-item dataset. Far future. No public manga user-rating dataset exists —
  searched, found none. Must be crawled from Jikan `/users/{name}/mangalist`,
  which needs a username source and a multi-day rate-limited run. It is a second
  ingestion source, not a download. Everything below that depends on it stays
  blocked; content-based recommendation does not.
- Item factors, not a similarity matrix. Factorize offline, store item vectors
  in `manga_embeddings.cf_vec`, query with the same HNSW. 160k x 160k is 102 GB.
- Hybrid blend. Weighted sum of content and CF scores, one tunable weight.
  Content-only until CF exists, so cold start already works.
- Bayesian score shrinkage. `raw_score` on 12 votes must not outrank 40k votes.
  Prior toward the global mean, weight by `votes_count`. Belongs in `derive`.
- LLM query understanding. Free-text prompt -> filters plus an embedding.
  Last, and only if plain vector search is not enough.

## Code quality
- Why no tenacity for retry mechanism in ingestion
- `get_or_create_tag` ignores `category` and `is_explicit` for a stored tag,
  while `bulk_get_or_create_tags` merges both. Only ingestion uses the bulk
  path, so nothing is wrong today. Make the two agree before a second caller
  arrives.
