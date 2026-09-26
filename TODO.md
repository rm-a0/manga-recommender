# TODO

Planned work, not yet scheduled.

## Ingestion

- Per-source ingest mode flags (`--create-only` / `--update-only`), so a second
  source can refresh ratings without overwriting the first one's metadata.
  Depends on splitting `ingestion/` into catalogue vs. user-signal submodules.
- Bound the 429 retry depth. It resets `attempt` to 1 and recurses.
- Backpressure on the fetch side. `_stream` schedules every chunk at once, and
  only the consumer is throttled.
- Update author name cleanup and formating

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

## Recommender

Order: configurable engine -> AniList signals -> collab -> franchise -> eval ->
tuning. Starts after the frontend merge.

### 1. Configurable engine

- Expose `_RANK_CONSTANT`, `_OVERFETCH_FACTOR`, `_OVERFETCH_FLOOR` and the
  dislike `_MAX_DISTANCE` as request fields. No settings class, no env vars:
  the default is `Field(0.9, ge=0, le=1)` on the request, visible in OpenAPI.
  A tuned value is a code change.
- Flat fields on `RecommendationRequest` and `RecommendationQuery`. No
  grouping classes. Defaults are `DEFAULT_*: Final` constants in
  `recommender/base.py`, applied only by the request (`Field(DEFAULT_X, ...)`).
  The query has no defaults and is `kw_only`: `_to_query` passes every field,
  so a request field it forgets fails loudly instead of being ignored. Tests
  and the eval build queries from a factory plus `dataclasses.replace`.
- `candidates_per_source` is a fixed default (200), with no floor or formula.
  An explicit value is used as given. Raise the default if the `limit` cap
  grows.
- Echo the resolved values in `RecommendationResult`, so a run is reproducible.
- Bound every field. It is a public engine. `liked_ids`, `exclude_ids` and
  `exclude_tags` have no `max_length` today. Pool size drives
  `hnsw.ef_search`, so cap it (~1000). `rank_constant >= 1`.
- Thresholds in similarity terms (cosine 0..1, higher = closer), never raw
  negative inner product. Convert inside the repository. The raw value is
  pgvector's convention and shifts with the embedding model.
- Keep the dislike threshold and a liked near-duplicate threshold separate.
  They answer different questions.

### 2. Catalogue filters

- `year_from` / `year_to`, `types`, `statuses`, `include_tags` (decide any vs
  all), `exclude_tags` (exists), `min_score` (`bayesian_score`), `min_votes`,
  maybe `exclude_explicit`. `year_from <= year_to` in a model validator.
- `min_votes` doubles as a popularity floor, which drops most art books and
  guidebooks.
- NULL semantics: `published_date` and `type` are nullable, and a manga with no
  `manga_metrics` row has no score. Make it explicit (`include_unknown: bool`).
- Push catalogue filters into the source queries, not post-filters. Strict
  filters otherwise starve the 200-candidate pool. One `WHERE` builder shared by
  the kNN and tags queries. Filtered HNSW returns fewer than `k` rows: use
  `hnsw.iterative_scan = relaxed_order` (pgvector >= 0.8). Seed-dependent
  filters (dislikes, franchise) stay post-filters.

### 3. AniList recommendations and relations

- Add `recommendations(perPage: 25, sort: RATING_DESC)` and `relations` to
  `MANGA_QUERY`. Check query complexity on one chunk. `chunk_size` may drop.
- Store raw edges by external id, resolve to `manga_id` in a pipeline stage.
  Targets are often in another chunk or not ingested.
  `manga_external_ratings(source_id, external_id)` already maps them.
- Relations include anime nodes: keep `type == MANGA` only.
- Franchise = connected components over SEQUEL, PREQUEL, SIDE_STORY, SPIN_OFF,
  ALTERNATIVE, PARENT, SUMMARY. Not CHARACTER or OTHER: crossovers glue
  unrelated series into one giant component.

### 4. Collab source

- One public `collab` source. AniList and Goodreads are provenance, not
  strategies, so neither name reaches the API.
- Raw signal tables per origin -> `collab` stage -> `manga_neighbours(manga_id,
  neighbour_id, score)`, top ~50 per manga. Sparse, not a dense matrix.
- Stage: normalize per source per row, symmetrize (A->B implies B->A, take
  max), weighted sum, top-N. One input today. Do not build a plugin framework
  for one input.
- Keep the merge a pure function (edges in -> neighbours out), apart from DB
  I/O. Production feeds it all edges. An eval can feed it a subset in memory
  and never touch the production table.
- Source: same shape as `ContentCandidateSource` -> `SeedMatches` ->
  `round_robin_merge`. Add to `_SOURCE_MAP` and the strategies.
- Reason text: "Readers who liked X also liked this".
- Goodreads later, as the extensibility exercise. Local UCSD comics dump.
  Collapse volumes to series, fuzzy-match title + author (`rapidfuzz`), store a
  confidence. Similarity by normalized co-occurrence (binary cosine or lift),
  min co-count ~5, "liked" = rating >= 4. Heavy franchise noise.

### 5. Franchise handling

- Filter: drop candidates in a seed's franchise. Or a selector: at most one per
  franchise. Exposed as `hide_same_series: bool = True`, not a number.
- Fallback where relations are missing: `similarity > t AND (shared author OR
  title-token overlap)`, applied to liked seeds.
- Calibrate `t` from relations: cosine histogram of franchise pairs vs
  non-franchise top-10 neighbours.
- Consider dropping `Title:` from `build_embedding_text`. Full re-embed, so
  measure first.
- Frontend option: a separate "More in this series" row.

### 6. Eval harness (hand-coded)

- Ground truth: AniList rec pairs (item -> item). Goodreads user hold-out later,
  as a second, independent eval.
- Never score collab on the pairs it is built from: it returns the answer key.
- Edge hold-out is degenerate for a one-hop lookup. A held-out pair A-B never
  comes back from seed A alone. Decide first:
  - Independent ground truth (preferred): MAL recommendations via Jikan
    `/manga/{id}/recommendations` for a sample of seeds. Collab keeps 100% of
    AniList edges, no split. Correlated with AniList, so read it as optimistic.
  - Edge k-fold only if collab becomes a derived similarity (shared
    rec-neighbourhoods, item vectors) that can predict unseen pairs. Then
    `hash(sorted pair) % k`, both directions held out together.
- Split the eval seeds, not the edges, for tuning: tune on one half, report on
  the other. Production data stays whole.
- Report seeds with no collab neighbours separately (cold start).
- Metrics: recall@k, nDCG@k, hit-rate@k. Beyond accuracy: franchise leakage,
  median `votes_count` of results, catalogue coverage, intra-list diversity.
- Baselines: random, top-k by popularity, content-only, tags-only, fused.
- Golden set: 20-30 known seeds with "should appear" / "must not appear".
- Design for extensibility and tests: ground-truth loaders, splitters, metrics
  and baselines as separate, swappable parts.

### 7. Tuning and later ideas

- Sweep source weights, `rank_constant`, `candidates_per_source`, cutoffs.
  Pick knees on leakage vs recall.
- Quality prior scorer: blend RRF with `bayesian_score` / `log(votes_count)`.
  Measure it, because popularity inflates recall on biased ground truth.
- IDF-weighted tag overlap. Use AniList tag `rank`.
- MMR diversity selector before `take_top_k`.
- Embedding text cleanup (strip "(Source: ...)"), larger model than
  `bge-small-en-v1.5`.

## Pipeline

Stages run in order: `fill` -> `export` -> `embed` -> `index` -> `train`.
Registry order is the run order, so `--stage` accepts any order.

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
