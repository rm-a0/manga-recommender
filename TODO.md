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

## Not built yet

- The authors and tags resources: schemas, services and routes.
- The recommendation engine, including semantic search over descriptions.
