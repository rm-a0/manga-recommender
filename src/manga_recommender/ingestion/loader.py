"""Persist extracted manga records to the database."""

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.repositories.genres import (
    bulk_get_or_create_genres,
)
from manga_recommender.db.repositories.manga import (
    bulk_add_genres_to_manga,
    bulk_update_or_create_manga,
)
from manga_recommender.db.repositories.manga_external_rating import (
    update_or_create_external_rating,
)
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.base import NormalizedMangaRecord


def _sync_genres_for_manga(
    db: Session,
    genre_cache: dict[str, uuid.UUID],
    normalized_genre_names: Iterable[str],
    manga_to_genre_map: dict[uuid.UUID, Sequence[str]],
) -> None:
    """Attach the given genre names to a manga, creating any that don't exist.

    Genre names are normalized to lowercase before lookup.
    """
    uncached = [n for n in normalized_genre_names if n not in genre_cache]
    if uncached:
        genre_cache.update(bulk_get_or_create_genres(db, uncached))
    name_id_map = {n: genre_cache[n] for n in normalized_genre_names}
    # Map manga IDs to genre IDs for bulk insertion
    manga_to_genre_ids_map = {
        manga_id: [name_id_map[g] for g in genres]
        for manga_id, genres in manga_to_genre_map.items()
    }
    pairs = [
        (manga_id, genre_id)
        for manga_id, genre_ids in manga_to_genre_ids_map.items()
        for genre_id in genre_ids
    ]
    bulk_add_genres_to_manga(db, pairs)


def _get_manga_genre_map_from_records(
    records: Sequence[NormalizedMangaRecord],
    external_id_to_manga_id: dict[str, uuid.UUID],
) -> dict[uuid.UUID, Sequence[str]]:
    """Return a mapping of manga IDs to the normalized genre names found in the given records."""
    return {
        external_id_to_manga_id[r.external_id]: [g.lower() for g in r.genres]
        for r in records
        if r.genres
    }


def load_batch(
    records: Sequence[NormalizedMangaRecord],
    source_id: uuid.UUID,
    genre_cache: dict[str, uuid.UUID],
) -> None:
    """Persist a batch of normalized manga records to the database in one transaction.

    Manga rows are bulk-upserted. Genre sync and rating upserts still run one
    record at a time — see TODO.md for the remaining bulk-load work.
    """
    with session_scope() as session:
        external_id_to_manga_id = bulk_update_or_create_manga(
            session,
            records,
            source_id,
        )
        manga_to_genre_map = _get_manga_genre_map_from_records(
            records,
            external_id_to_manga_id,
        )
        normalized_genre_names = {
            g for genres in manga_to_genre_map.values() for g in genres
        }
        _sync_genres_for_manga(
            session,
            genre_cache,
            normalized_genre_names,
            manga_to_genre_map,
        )
        for record in records:
            manga_id = external_id_to_manga_id[record.external_id]
            # bulk_update_or_create_manga returns ids, not ORM objects, so
            # re-fetch the row to mutate its genres relationship.
            update_or_create_external_rating(
                session,
                manga_id=manga_id,
                source_id=source_id,
                external_id=record.external_id,
                raw_scale_max=record.raw_scale_max,
                votes_count=record.votes_count,
                fetched_at=record.fetched_at,
                raw_score=record.raw_score,
            )
