"""Persist extracted manga records to the database."""

import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.repositories.genres import (
    bulk_get_or_create_genres,
)
from manga_recommender.db.repositories.manga import (
    MangaUpsertValues,
    bulk_add_genres_to_manga,
    bulk_update_or_create_manga,
)
from manga_recommender.db.repositories.manga_external_rating import (
    RatingUpsertValues,
    bulk_update_or_create_external_ratings,
)
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.base import NormalizedMangaRecord


def _sync_genres_for_manga(
    db: Session,
    genre_cache: dict[str, uuid.UUID],
    normalized_genre_names: Iterable[str],
    manga_to_genre_map: dict[uuid.UUID, Sequence[str]],
) -> None:
    """Resolve genre names to ids and bulk-attach them to their manga.

    A cache miss triggers one bulk lookup-or-create query for all misses.
    """
    uncached = [n for n in normalized_genre_names if n not in genre_cache]
    if uncached:
        genre_cache.update(bulk_get_or_create_genres(db, uncached))
    name_id_map = {n: genre_cache[n] for n in normalized_genre_names}
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
    """Map each manga id to its lowercased genre names.

    Skips records with no genres instead of mapping them to an empty list.
    """
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

    Manga and genre writes are bulk-upserted. Rating upserts still run one
    record at a time — see TODO.md.
    """
    with session_scope() as session:
        external_id_to_manga_id = bulk_update_or_create_manga(
            session,
            source_id,
            records=[
                MangaUpsertValues(
                    mal_id=r.mal_id,
                    title=r.title,
                    author=r.author,
                    published_date=r.published_date,
                    description=r.description,
                    status=r.status,
                    external_id=r.external_id,
                )
                for r in records
            ],
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
        bulk_update_or_create_external_ratings(
            session,
            values=[
                RatingUpsertValues(
                    manga_id=external_id_to_manga_id[r.external_id],
                    source_id=source_id,
                    external_id=r.external_id,
                    raw_scale_max=r.raw_scale_max,
                    votes_count=r.votes_count,
                    fetched_at=r.fetched_at,
                    raw_score=r.raw_score,
                )
                for r in records
            ],
        )
