# TODO

Deferred ideas worth remembering, not yet scheduled.

## Ingestion

- **Per-source ingest mode flags** (`--create-only` / `--update-only` / off, per
  source). Motivating case: an outdated Kaggle catalogue dump you don't want
  re-created from, only refreshing ratings from AniList going forward. Depends on
  first splitting `ingestion/` into submodules (catalogue vs. user-signal
  ingestion), so the flag design should follow that split, not be bolted on now.
- **The loader, not fetching, is the real bottleneck.** ~18-20s per 50-record
  batch (per-record round trips: manga upsert, genre lookup-or-create, rating
  upsert) — a full-catalogue backfill (~175k manga) would take ~17+ hours to
  load even though fetching alone takes ~2h. Fix: bulk
  `INSERT ... ON CONFLICT DO UPDATE` per batch instead of per-record upserts,
  plus an in-memory genre cache to avoid a lookup-or-create round trip per
  genre per manga.
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
