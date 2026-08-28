"""Data-access functions for the MangaExternalRating model."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_external_ratings import MangaExternalRating


class RatingUpsertValues(TypedDict):
    """Column values for one bulk-upserted external rating row."""

    manga_id: uuid.UUID
    source_id: uuid.UUID
    external_id: str
    raw_scale_max: float | None
    votes_count: int | None
    fetched_at: datetime
    raw_score: float | None
    score_distribution: list[int] | None


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
    score_distribution: list[int] | None = None,
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
        score_distribution=score_distribution,
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
    score_distribution: list[int] | None = None,
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
    score_distribution: list[int] | None = None,
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
            score_distribution=score_distribution,
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
        score_distribution=score_distribution,
    )


# --- Bulk operations ---


def bulk_update_or_create_external_ratings(
    db: Session,
    values: Sequence[RatingUpsertValues],
) -> None:
    """Upsert a batch of external ratings in one round trip.

    Conflicts on (manga_id, source_id) overwrite existing fields; NULLs are
    coalesced against the current row instead of clearing it.
    """
    values = list({v["manga_id"]: v for v in values}.values())
    insert_stmt = pg_insert(MangaExternalRating).values(values)
    stmt = insert_stmt.on_conflict_do_update(
        index_elements=["manga_id", "source_id"],
        set_={
            "external_id": func.coalesce(
                insert_stmt.excluded.external_id, MangaExternalRating.external_id
            ),
            "raw_scale_max": func.coalesce(
                insert_stmt.excluded.raw_scale_max, MangaExternalRating.raw_scale_max
            ),
            "votes_count": func.coalesce(
                insert_stmt.excluded.votes_count, MangaExternalRating.votes_count
            ),
            "fetched_at": func.coalesce(
                insert_stmt.excluded.fetched_at, MangaExternalRating.fetched_at
            ),
            "raw_score": func.coalesce(
                insert_stmt.excluded.raw_score, MangaExternalRating.raw_score
            ),
            "score_distribution": func.coalesce(
                insert_stmt.excluded.score_distribution,
                MangaExternalRating.score_distribution,
            ),
        },
    )
    db.execute(stmt)
