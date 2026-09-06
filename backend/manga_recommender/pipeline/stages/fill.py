"""Recompute the derived rating metrics for every manga."""

from collections.abc import Sequence
from datetime import UTC, datetime

import structlog
from sqlalchemy import Row
from sqlalchemy.orm import Session

from manga_recommender.core.config import get_pipeline_settings
from manga_recommender.db.repositories.manga_external_rating import (
    get_rating_aggregates,
)
from manga_recommender.db.repositories.manga_metrics import (
    MetricValues,
    bulk_create_manga_metrics,
    delete_all_manga_metrics,
)
from manga_recommender.db.session import session_scope

logger = structlog.get_logger(__name__)


def _compute_bayesian_average(
    weighted_numerator: float,
    weighted_denominator: float,
    catalogue_mean: float,
    smoothing_votes: float,
) -> float:
    """Return the mean score pulled toward the catalogue mean.

    `smoothing_votes` acts as that many imaginary votes at the catalogue mean.
    A manga with few votes moves close to that mean. A manga with many votes
    keeps its own mean.
    """
    return (weighted_numerator + catalogue_mean * smoothing_votes) / (
        weighted_denominator + smoothing_votes
    )


def _compute_mean(weighted_numerator: float, weighted_denominator: float) -> float:
    """Return the weighted mean score for one set of rating sums."""
    return weighted_numerator / weighted_denominator


def _compute_catalogue_mean(rows: Sequence[Row]) -> float:
    """Return the mean score across every rated manga.

    This is the value that `_compute_bayesian_average` shrinks toward. The
    caller must not pass an empty sequence.
    """
    return _compute_mean(
        weighted_numerator=sum([row.weighted_numerator for row in rows]),
        weighted_denominator=sum([row.weighted_denominator for row in rows]),
    )


def replace_manga_metrics(
    db: Session,
    rows: Sequence[MetricValues],
    batch_size: int,
) -> None:
    """Replace every metric row with a recomputed set.

    Deletes the old rows, then inserts the new ones in batches. Every step
    shares one transaction, so a reader never sees the table empty.
    """
    deleted_count = delete_all_manga_metrics(db)
    logger.info("metrics_deleted", count=deleted_count)
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        bulk_create_manga_metrics(db, batch)
    logger.info("metrics_created", count=len(rows))


def compute_manga_metrics(
    db: Session,
    smoothing_votes: float,
) -> Sequence[MetricValues]:
    """Compute one metric row for every manga that has a usable rating.

    Reads nothing but the rating aggregates, so the whole catalogue needs one
    query. Every row carries the same `computed_at`, because one call is one
    recomputation.
    """
    rows = get_rating_aggregates(db)
    if not rows:
        return []
    timestamp = datetime.now(UTC)
    catalogue_mean = _compute_catalogue_mean(rows)
    return [
        MetricValues(
            manga_id=row.manga_id,
            bayesian_score=_compute_bayesian_average(
                weighted_numerator=row.weighted_numerator,
                weighted_denominator=row.weighted_denominator,
                catalogue_mean=catalogue_mean,
                smoothing_votes=smoothing_votes,
            ),
            mean_score=_compute_mean(row.weighted_numerator, row.weighted_denominator),
            votes_count=row.votes_count,
            source_count=row.sources_count,
            computed_at=timestamp,
        )
        for row in rows
    ]


def run_fill() -> None:
    """Recompute every metric row from the current external ratings."""
    settings = get_pipeline_settings()
    with session_scope() as session:
        replace_manga_metrics(
            session,
            compute_manga_metrics(session, settings.smoothing_votes),
            settings.batch_size,
        )
