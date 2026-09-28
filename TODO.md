# TODO

Planned work, not yet scheduled.

## Ingestion

- Update author name cleanup and formating

## Database

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

## Recommender

Order: configurable engine -> AniList signals -> collab -> franchise -> eval ->
tuning. Starts after the frontend merge.

### 3. AniList recommendations and relations

- Add `recommendations(perPage: 25, sort: RATING_DESC)` and `relations` to
  `MANGA_QUERY`. Check query complexity on one chunk. `chunk_size` may drop.
- The DB stores only computed results. A separate signals extractor
  (`ingestion/signals/`) writes the raw edges, by external id, to artifacts
  (`data/artifacts/edges/`), like `export_manga` does. The catalogue extractor stays
  as it is. Both share one `AnilistClient` for rate limit and retries. Rebuilding the matrix then needs no re-fetch, and the eval
  reads the same raw pairs. A pipeline stage resolves the ids to `manga_id`
  through `manga_external_ratings(source_id, external_id)`.
- Relations include anime nodes: keep `type == MANGA` only.
- Franchise = connected components over SEQUEL, PREQUEL, SIDE_STORY, SPIN_OFF,
  ALTERNATIVE, PARENT, SUMMARY. Not CHARACTER or OTHER: crossovers glue
  unrelated series into one giant component.

### 4. Collab source

- One public `collab` source. AniList and Goodreads are provenance, not
  strategies, so neither name reaches the API.
- Raw edge artifacts per origin -> `collab` stage -> `manga_neighbours(manga_id,
  neighbour_id, score)`, top ~50 per manga. Sparse, not a dense matrix. One
  merged score, not a column per source: a column per source needs a
  migration for each new source. If per-source weights must ever be tunable
  at request time, switch to a `source_id` column instead.
- Relations -> `franchise` stage -> one franchise id per manga.
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
- A liked near-duplicate cutoff stays separate from the dislike cutoff. They
  answer different questions.
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

Stages run in order: `compute_metrics` -> `export_manga` -> `embed_manga` -> `load_embeddings` -> `train`.
Registry order is the run order, so `--stage` accepts any order.

- `load_embeddings`: `.npz` -> `manga_embeddings`, then build HNSW. Load the rows before
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

- Content embeddings. Description + tags -> `halfvec(384)`, HNSW. See `embed_manga`.
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
