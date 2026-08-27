# TODO

Deferred ideas worth remembering, not yet scheduled.

## Ingestion

- **Per-source ingest mode flags** (`--create-only` / `--update-only` / off, per
  source). Motivating case: an outdated Kaggle catalogue dump you don't want
  re-created from, only refreshing ratings from AniList going forward. Depends on
  first splitting `ingestion/` into submodules (catalogue vs. user-signal
  ingestion), so the flag design should follow that split, not be bolted on now.
- **One non-429 failure kills the whole fetch.** `_fetch_all`'s
  `asyncio.gather()` has no `return_exceptions=True` and no retry beyond 429 —
  a single 500/timeout/malformed response anywhere across ~3,700 chunk
  requests loses the entire run, since nothing is yielded until every chunk
  finishes. Accepted as a risk for now; revisit if a real run actually hits it.
- `runner.py`'s `ingestion_completed` log sits outside the `try`/`except`, so
  it fires even right after `ingestion_failed` for the same source. Should
  move inside the `try` block so it only logs on actual success.

