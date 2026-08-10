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
