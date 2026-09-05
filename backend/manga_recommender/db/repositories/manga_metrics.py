"""Data-access functions for the MangaMetric model."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import TypedDict, cast

from sqlalchemy import CursorResult, delete, insert, select
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_metrics import MangaMetric


class MetricValues(TypedDict):
    """Column values for one bulk-inserted metric row."""

    manga_id: uuid.UUID
    bayesian_score: float
    mean_score: float
    votes_count: int
    source_count: int
    computed_at: datetime


def create_manga_metric(
    db: Session,
    *,
    manga_id: uuid.UUID,
    bayesian_score: float,
    mean_score: float,
    votes_count: int,
    source_count: int,
    computed_at: datetime,
) -> MangaMetric:
    """Create and persist a new metric row."""
    db_manga_metric = MangaMetric(
        manga_id=manga_id,
        bayesian_score=bayesian_score,
        mean_score=mean_score,
        votes_count=votes_count,
        source_count=source_count,
        computed_at=computed_at,
    )
    db.add(db_manga_metric)
    db.flush()
    return db_manga_metric


def get_manga_metric_by_manga_id(
    db: Session,
    manga_id: uuid.UUID,
) -> MangaMetric | None:
    """Return the metric row for the given manga, or None if not found."""
    return db.scalar(select(MangaMetric).where(MangaMetric.manga_id == manga_id))


def update_manga_metric(
    db: Session,
    manga_metric: MangaMetric,
    *,
    manga_id: uuid.UUID,
    bayesian_score: float,
    mean_score: float,
    votes_count: int,
    source_count: int,
    computed_at: datetime,
) -> MangaMetric:
    """Overwrite every field of a metric row and return it.

    Every field is required. The `fill` stage recomputes a row as a whole, so
    a partial update would leave the row inconsistent with itself.
    """
    updates = {
        "manga_id": manga_id,
        "bayesian_score": bayesian_score,
        "mean_score": mean_score,
        "votes_count": votes_count,
        "source_count": source_count,
        "computed_at": computed_at,
    }
    for field, value in updates.items():
        setattr(manga_metric, field, value)
    db.flush()
    return manga_metric


def update_or_create_manga_metric(
    db: Session,
    *,
    manga_id: uuid.UUID,
    bayesian_score: float,
    mean_score: float,
    votes_count: int,
    source_count: int,
    computed_at: datetime,
) -> MangaMetric:
    """Return the metric row for the given manga, updating or creating it.

    Use this for a single manga. The `fill` stage recomputes the whole table
    and uses the bulk functions instead.
    """
    manga_metric = get_manga_metric_by_manga_id(db, manga_id)
    if manga_metric:
        return update_manga_metric(
            db,
            manga_metric=manga_metric,
            manga_id=manga_id,
            bayesian_score=bayesian_score,
            mean_score=mean_score,
            votes_count=votes_count,
            source_count=source_count,
            computed_at=computed_at,
        )
    return create_manga_metric(
        db,
        manga_id=manga_id,
        bayesian_score=bayesian_score,
        mean_score=mean_score,
        votes_count=votes_count,
        source_count=source_count,
        computed_at=computed_at,
    )


# --- Bulk operations ---


def delete_all_manga_metrics(db: Session) -> int:
    """Delete every metric row and return the number removed.

    The `fill` stage clears the table before it writes the recomputed rows.
    """
    # RETURNING sends back one id per manga in the catalogue. Count instead.
    result = cast(CursorResult, db.execute(delete(MangaMetric)))
    return result.rowcount


def bulk_create_manga_metrics(db: Session, values: Sequence[MetricValues]) -> None:
    """Insert a batch of metric rows in one round trip.

    The caller clears the table first. There is no conflict clause, so a row
    that already exists for the same manga raises.
    """
    if not values:
        return
    db.execute(insert(MangaMetric), values)
