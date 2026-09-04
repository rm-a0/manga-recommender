# TODO

Planned work, not yet scheduled.

## Ingestion

- Per-source ingest mode flags (`--create-only` / `--update-only`), so a second
  source can refresh ratings without overwriting the first one's metadata.
  Depends on splitting `ingestion/` into catalogue vs. user-signal submodules.
- Bound the 429 retry depth. It resets `attempt` to 1 and recurses.
- Backpressure on the fetch side. `_stream` schedules every chunk at once, and
  only the consumer is throttled.
- Fetch AniList's `english`, `native` and `synonyms` titles, plus structured
  `name { first last native }` for staff. Both need a re-ingest.

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
- Narrow `manga.published_date` from `DateTime(timezone=True)` to `Date`. Neither
  source carries a time: Kaggle gives `YYYY-MM-DD` and AniList gives
  `{year, month, day}`, so both extractors build a midnight datetime that means
  nothing. Saves 4 bytes a row, drops the timezone question, and lets the API's
  `published_from`/`published_to` filters compare date to date instead of a naive
  datetime against a tz-aware column. `ALTER COLUMN ... TYPE date` casts in place,
  so no re-ingest. Touches the model, `MangaUpsertValues`, `MangaDetail`, both
  extractors and `ingestion/base.py`, plus ~25 test references.
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
- Sorting by score. `raw_score` sits on `manga_external_ratings` against a
  per-source `raw_scale_max`, so ordering by it means normalizing and aggregating
  per row. Needs a normalized score column on `manga`, written at ingest —
  the same shape as the arbitration column the database section already wants.
- An index on `manga.title`. Every page already pays a full sort for
  `ORDER BY title OFFSET n`.

## Not built yet

- The recommendation engine, including semantic search over descriptions.
