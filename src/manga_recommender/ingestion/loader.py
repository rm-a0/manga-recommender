"""Persist extracted manga records to the database."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.repositories.genres import get_or_create_genre
from manga_recommender.db.repositories.manga import (
    add_genres_to_manga,
    bulk_update_or_create_manga,
)
from manga_recommender.db.repositories.manga_external_rating import (
    update_or_create_external_rating,
)
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.base import NormalizedMangaRecord


def _sync_genres_for_manga(
    db: Session,
    db_manga: Manga,
    genre_names: list[str],
) -> None:
    """Attach the given genre names to a manga, creating any that don't exist.

    Genre names are normalized to lowercase before lookup.
    """
    genres = [
        get_or_create_genre(db, name=genre_name.strip().casefold())
        for genre_name in genre_names
    ]
    add_genres_to_manga(db, db_manga, genres)


def load_batch(records: Sequence[NormalizedMangaRecord], source_id: uuid.UUID) -> None:
    """Persist a batch of normalized manga records to the database in one transaction."""
    with session_scope() as session:
        id_map = bulk_update_or_create_manga(session, records, source_id)
        for record in records:
            manga_id = id_map[record.external_id]
            db_manga = session.get(Manga, manga_id)
            if record.genres and db_manga:
                _sync_genres_for_manga(session, db_manga, record.genres)
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
