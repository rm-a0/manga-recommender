# TODO

Deferred ideas worth remembering, not yet scheduled.

## Ingestion

- **Per-source ingest mode flags** (`--create-only` / `--update-only` / off, applying per
  source, e.g. `--source anilist:update-only --source kaggle:off`). Motivating case: an
  outdated Kaggle catalogue dump you don't want re-created from, only refreshing ratings
  from AniList going forward. Left out for now — depends on first splitting `ingestion/`
  into submodules (catalogue/manga ingestion vs. user-signal ingestion from other
  datasets), so the flag design should follow that split rather than be bolted onto the
  current single-module shape.

## Testing

- **Run tests against a local Docker Postgres instead of the real Supabase DB.**
  Motivating case: `test_manga.py` hardcodes small literal `mal_id`s (1, 2, 3), which
  now collide with real AniList data seeded into the same `DB_URL` by the actual
  ingestion run — `db_session`'s rollback only protects what happens inside a test, not
  against data already committed by something else beforehand. Once tests point at an
  isolated local DB with no real seed data, this collision goes away on its own — no
  code fix needed in the meantime.
