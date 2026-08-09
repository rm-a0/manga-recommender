"""Data-access functions for the MangaExternalRating model."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_external_ratings import MangaExternalRating


def create_external_rating(
    db: Session,
    *,
    manga_id: uuid.UUID,
    source_id: uuid.UUID,
    external_id: str,
    raw_scale_max: float | None = None,
    votes_count: int | None = None,
    fetched_at: datetime,
    raw_score: float | None = None,
) -> MangaExternalRating:
    """Create and persist a new external rating."""
    db_external_rating = MangaExternalRating(
        manga_id=manga_id,
        source_id=source_id,
        external_id=external_id,
        raw_scale_max=raw_scale_max,
        votes_count=votes_count,
        fetched_at=fetched_at,
        raw_score=raw_score,
    )
    db.add(db_external_rating)
    db.flush()
    return db_external_rating


def update_external_rating(
    db: Session,
    external_rating: MangaExternalRating,
    *,
    raw_scale_max: float | None = None,
    votes_count: int | None = None,
    fetched_at: datetime | None = None,
    raw_score: float | None = None,
) -> MangaExternalRating:
    """Update the given external rating's fields and persist the changes.

    Only fields with a non-None value are updated.
    """
    updates = {
        "raw_scale_max": raw_scale_max,
        "votes_count": votes_count,
        "fetched_at": fetched_at,
        "raw_score": raw_score,
    }
    for field, value in updates.items():
        if value is not None:
            setattr(external_rating, field, value)
    db.flush()
    return external_rating


def get_external_rating_by_manga_and_source(
    db: Session,
    manga_id: uuid.UUID,
    source_id: uuid.UUID,
) -> MangaExternalRating | None:
    """Return the external rating for the given manga and source, or None if not found."""
    return db.scalar(
        select(MangaExternalRating).where(
            MangaExternalRating.manga_id == manga_id,
            MangaExternalRating.source_id == source_id,
        )
    )


def update_or_create_external_rating(
    db: Session,
    *,
    manga_id: uuid.UUID,
    source_id: uuid.UUID,
    external_id: str,
    raw_scale_max: float | None = None,
    votes_count: int | None = None,
    fetched_at: datetime,
    raw_score: float | None = None,
) -> MangaExternalRating:
    """Update the matching external rating if one exists, otherwise create it."""
    external_rating = get_external_rating_by_manga_and_source(db, manga_id, source_id)
    if external_rating:
        return update_external_rating(
            db,
            external_rating,
            raw_scale_max=raw_scale_max,
            votes_count=votes_count,
            fetched_at=fetched_at,
            raw_score=raw_score,
        )
    return create_external_rating(
        db,
        manga_id=manga_id,
        source_id=source_id,
        external_id=external_id,
        raw_scale_max=raw_scale_max,
        votes_count=votes_count,
        fetched_at=fetched_at,
        raw_score=raw_score,
    )
