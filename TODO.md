# TODO

Deferred ideas worth remembering, not yet scheduled.

## Ingestion

- **Per-source ingest mode flags** (`--create-only` / `--update-only` / off, per
  source). Motivating case: an outdated Kaggle catalogue dump you don't want
  re-created from, only refreshing ratings from AniList going forward. Depends on
  first splitting `ingestion/` into submodules (catalogue vs. user-signal
  ingestion), so the flag design should follow that split, not be bolted on now.
- **The loader, not fetching, is the real bottleneck — manga upsert is now
  bulk, genre/rating still aren't, and a timed run shows that's most of the
  cost.** `bulk_update_or_create_manga` (`db/repositories/manga.py`) replaced
  the per-record manga upsert with one `INSERT ... ON CONFLICT DO UPDATE` per
  batch, falling back to the old per-record path only for the rare record
  with no `mal_id` (a NULL `mal_id` never matches another NULL under
  Postgres's `ON CONFLICT`, so those can't take the bulk path — see
  `ingestion/README.md`). A live timed run (`ANILIST_MAX_ID=30201`) confirmed
  every record took the bulk path, but batches still took 14-17.5s for 50
  records, barely under the original ~18-20s baseline. Genre lookup-or-create
  and rating upsert are the real remaining cost — both still run per record
  in `loader.py`'s `load_batch`. At this rate a full ~175k-manga backfill is
  still ~16h.
  Next: mirror the same bulk pattern for the rest of `load_batch`:
  - an in-memory genre cache, to avoid a `SELECT`/`INSERT` round trip per
    genre name per manga (`get_or_create_genre` in `db/repositories/genres.py`)
  - a bulk insert for the `manga_genres` junction rows, replacing
    `add_genres_to_manga`'s per-manga lazy-load + append loop
  - a bulk `INSERT ... ON CONFLICT DO UPDATE` for `manga_external_ratings`,
    same shape as `bulk_update_or_create_manga`
  - once genre sync is bulked, `load_batch`'s per-record
    `session.get(Manga, manga_id)` can go too — it only exists today to get
    an ORM object for `_sync_genres_for_manga` to mutate, since
    `bulk_update_or_create_manga` returns ids, not ORM objects.
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
