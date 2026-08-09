# Ingestion

Pulls manga metadata and per-source ratings from external providers into the database.
One-shot offline job, not triggered by the API.

## Modules

- `base.py` — `BaseExtractor` interface + `NormalizedMangaRecord`, the shape every
  extractor yields.
- `anilist.py` — `AnilistExtractor`, pulls from AniList's GraphQL API.
- `registry.py` — maps a source name to its extractor class and default seed weight.
  The only place a new source needs to be registered.
- `loader.py` — `load_batch`: upserts `Manga`, syncs genres, upserts
  `MangaExternalRating`, given a `source_id`.
- `runner.py` — `run_ingestion`: for each source name, seeds the `Source` row via the
  registry's default weight, then batches the extractor's output into `load_batch`
  calls (`INGESTION_BATCH_SIZE` records per transaction).

## Why MAL ID is the matching key

`update_or_create_manga` matches an incoming record to an existing `Manga` row by
`mal_id` first, falling back to `(source_id, external_id)` only when `mal_id` is
`None`. This is what prevents the same title from being inserted twice as different
sources are ingested — the fallback only fires for manga that genuinely have no MAL
entry (AniList's `idMal` self-reports this as `None` rather than just omitting it), so
it never masks a manga that's already tracked under a real `mal_id` elsewhere.
