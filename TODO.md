# TODO

Deferred ideas worth remembering, not yet scheduled.

## Ingestion

- **Per-source ingest mode flags** (`--create-only` / `--update-only` / off, per
  source). Motivating case: an outdated Kaggle catalogue dump you don't want
  re-created from, only refreshing ratings from AniList going forward. Depends on
  first splitting `ingestion/` into submodules (catalogue vs. user-signal
  ingestion), so the flag design should follow that split, not be bolted on now.
- **The loader, not fetching, is the real bottleneck — manga and genres are
  now bulk, ratings still aren't.** `bulk_update_or_create_manga`
  (`db/repositories/manga.py`) replaced the per-record manga upsert with one
  `INSERT ... ON CONFLICT DO UPDATE` per batch, falling back to the old
  per-record path only for the rare record with no `mal_id` (a NULL `mal_id`
  never matches another NULL under Postgres's `ON CONFLICT`, so those can't
  take the bulk path — see `ingestion/README.md`). Genre resolution is bulk
  too: `bulk_get_or_create_genres` (`db/repositories/genres.py`)
  upsert-returns a whole batch's genre names in one round trip, backed by an
  in-memory `genre_cache` (owned by `run_ingestion`, threaded through
  `load_batch`) so any given genre name only ever hits the database once per
  run. `bulk_add_genres_to_manga` writes the `manga_genres` junction rows
  directly in one statement, bypassing the ORM relationship entirely — which
  also removed the per-record `session.get(Manga, manga_id)` that used to
  exist only to support it. A live timed run (`ANILIST_MAX_ID=30201`)
  confirmed the win: batches dropped from 14-17.5s to ~4.4-5.0s for 50
  records, roughly 3x, taking a full ~175k-manga backfill from ~16h down to
  ~4.5-5h.
  Next: `manga_external_ratings` is the one piece left running per record
  (`update_or_create_external_rating` in `loader.py`'s `load_batch`). Same
  shape as `bulk_update_or_create_manga` — one `INSERT ... ON CONFLICT DO
  UPDATE` per batch, conflict target `(manga_id, source_id)`.
- **One non-429 failure kills the whole fetch.** `_fetch_all`'s
  `asyncio.gather()` has no `return_exceptions=True` and no retry beyond 429 —
  a single 500/timeout/malformed response anywhere across ~3,700 chunk
  requests loses the entire run, since nothing is yielded until every chunk
  finishes. Accepted as a risk for now; revisit if a real run actually hits it.
- `runner.py`'s `ingestion_completed` log sits outside the `try`/`except`, so
  it fires even right after `ingestion_failed` for the same source. Should
  move inside the `try` block so it only logs on actual success.

## Data model

- **Store AniList's score distribution**, not just the summed `votes_count`.
  Add it as a native `ARRAY(Integer)` column (10 buckets) on
  `manga_external_ratings` rather than a normalized child table — a child
  table would be ~1.75M rows (175k manga × 10 buckets) with a UUID PK+FK each,
  versus one small array column per rating. Useful later as a rating-variance
  signal (a controversial title and a universally-loved one can share the same
  average score today).

## Testing

- **Run tests against a local Docker Postgres instead of the real Supabase DB.**
  No longer theoretical — a real ingestion run seeded real data, and
  `test_genres.py`/`test_manga.py`/`test_sources.py` now actively fail on
  unique-constraint collisions with hardcoded test literals (`mal_id=1/2/3`,
  `name="action"`, `name="anilist"`). `db_session`'s rollback only protects a
  test's own writes, not against data already committed by something else
  beforehand.
