# TODO

Deferred ideas worth remembering, not yet scheduled.

## Ingestion

- **Per-source ingest mode flags** (`--create-only` / `--update-only` / off, per
  source). Motivating case: an outdated Kaggle catalogue dump you don't want
  re-created from, only refreshing ratings from AniList going forward. Depends on
  first splitting `ingestion/` into submodules (catalogue vs. user-signal
  ingestion), so the flag design should follow that split, not be bolted on now.
- **The 429 retry path resets `attempt` to 1**, so it recurses without a depth
  limit. The `Retry-After` sleep keeps it harmless in practice.
- **Fetch-side backpressure is missing.** `_stream` turns all ~3,700 chunk
  coroutines into tasks at once. The bounded queue in `base.py` throttles the
  consumer only, so completed-but-unyielded chunks accumulate if the database
  falls behind. Fetch and load happen to run about 1:1 today.

## Database

- **The canonical-entry rule holds within a batch only.** `_pick_canonical_by_votes`
  keeps the highest-voted entry when several share a `mal_id`, but the conflict
  update still overwrites unconditionally, so two merged entries landing in
  different batches still let the later batch win. Making it durable needs an
  arbitration column on `manga` and a `WHERE` on the conflict update. Add it only
  if titles are seen to churn between runs.
- **No reconciliation for records without a `mal_id`.** An AniList entry with a
  null `idMal` gets a manga row identified only by `(anilist, external_id)`. The
  same series arriving from Kaggle MAL with a `mal_id` becomes a second manga row
  and nothing merges the two. Measure how many AniList entries lack `idMal`
  before choosing a fix — that number also drives ingest throughput, since
  `_bulk_upsert_without_mal_id` costs one or two queries per record.
- **Manga that only ever came from Kaggle have no authors yet.** Migration
  `f5a93d21c8e0` backfills only manga holding an AniList rating, because a comma
  split is wrong for Kaggle names ("Urasawa, Naoki" is one person). A Kaggle
  ingest fills them in and merges onto the existing author rows, but it cannot
  run until the metadata-overwrite problem below is solved.
- **Running a second source overwrites the first one's manga metadata.** The
  conflict update coalesces against the incumbent, so the source that runs last
  wins every field it has a value for. `title` always wins, because it is never
  null. Running Kaggle after AniList therefore replaces the AniList titles,
  descriptions and statuses across the whole shared catalogue. This is what the
  per-source `--update-only` flag above is for; until it exists, run only one
  source against a populated database.
- **Genre and author links only ever accumulate.** Both writers use
  `ON CONFLICT DO NOTHING`, and neither link table records which source added a
  row, so a second source adds links beside the first one's and a link nothing
  writes any more is never removed. Author *identity* is safe —
  `authors.normalized_name` folds spellings onto one row — but a genre or author
  a source drops between runs stays attached.
- **No `role` on `manga_authors`.** AniList distinguishes Story from Art and the
  extractor discards that. Kaggle gives no role at all, so a NOT NULL role column
  would be half empty. Worth adding once there is a use for it.
- **Coalesce upserts cannot return a value to NULL — decided, keep as is.**
  A stale value is preferred over no value. The known cost: if AniList withdraws
  a score, the stale `raw_score` persists while `fetched_at` still advances, so
  the row looks fresher than it is. Revisit only if the recommender needs to tell
  "scored long ago" from "scored just now".

## Next AniList re-ingest

Both items need a query change plus a full re-ingest, so do them in one pass.

- **Request the other title fields.** `MANGA_QUERY` asks for `title { romaji }`
  only. AniList also returns `english`, `native` and `synonyms`. These are the
  raw material for matching records that have no `mal_id` against records that
  do, and they cost nothing to add to the query.
- **Request structured author names.** `staff` asks for `name { full }`. AniList
  also returns `first`, `last` and `native`. `normalized_name` already folds
  word-order differences, so this is only needed for the cases it cannot reach:
  a native-script spelling against a romanized one.
