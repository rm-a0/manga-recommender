"""Recompute the derived rating metrics for every manga."""

import time
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


def _compute_bayesian_score(
    score_points: float,
    weighted_votes: float,
    catalogue_mean: float,
    smoothing_votes: float,
) -> float:
    """Return one manga's own mean score, pulled toward the catalogue mean.

    `smoothing_votes` acts as that many imaginary votes at the catalogue mean.
    A manga with few votes moves close to that mean. A manga with many votes
    keeps its own mean.
    """
    return (score_points + catalogue_mean * smoothing_votes) / (
        weighted_votes + smoothing_votes
    )


def _compute_mean(values_sum: float, values_count: float) -> float:
    """Divide a sum by a count and return the mean."""
    return values_sum / values_count


def _compute_catalogue_mean(aggregates: Sequence[Row]) -> float:
    """Return the mean score across every rated manga.

    Each manga counts once, whatever its vote count. This is the value that
    `_compute_bayesian_score` shrinks toward. The caller must not pass an
    empty sequence.
    """
    return _compute_mean(
        values_sum=sum(
            _compute_mean(agg.score_points, agg.weighted_votes) for agg in aggregates
        ),
        values_count=len(aggregates),
    )


def replace_manga_metrics(
    db: Session,
    metrics: Sequence[MetricValues],
    batch_size: int,
) -> None:
    """Replace every metric row with a recomputed set.

    Deletes the old rows, then inserts the new ones in batches. Every step
    shares one transaction, so a reader never sees the table empty.
    """
    deleted_count = delete_all_manga_metrics(db)
    logger.info("metrics_deleted", count=deleted_count)
    metrics_count = len(metrics)
    for i in range(0, metrics_count, batch_size):
        batch = metrics[i : i + batch_size]
        start_time = time.monotonic()
        bulk_create_manga_metrics(db, batch)
        logger.info(
            "batch_created",
            count=len(batch),
            elapsed_s=round(time.monotonic() - start_time, 1),
        )
    logger.info("metrics_created", count=metrics_count)


def compute_manga_metrics(
    db: Session,
    smoothing_votes: float,
) -> Sequence[MetricValues]:
    """Compute one metric row for every manga that has a usable rating.

    Reads nothing but the rating aggregates, so the whole catalogue needs one
    query. Every row carries the same `computed_at`, because one call is one
    recomputation.
    """
    aggregates = get_rating_aggregates(db)
    if not aggregates:
        return []
    timestamp = datetime.now(UTC)
    catalogue_mean = _compute_catalogue_mean(aggregates)
    metrics = [
        MetricValues(
            manga_id=agg.manga_id,
            bayesian_score=_compute_bayesian_score(
                score_points=agg.score_points,
                weighted_votes=agg.weighted_votes,
                catalogue_mean=catalogue_mean,
                smoothing_votes=smoothing_votes,
            ),
            mean_score=_compute_mean(agg.score_points, agg.weighted_votes),
            votes_count=agg.votes_count,
            source_count=agg.source_count,
            computed_at=timestamp,
        )
        for agg in aggregates
    ]
    logger.info("metrics_computed", count=len(metrics), catalogue_mean=catalogue_mean)
    return metrics


def run_fill() -> None:
    """Recompute every metric row from the current external ratings."""
    settings = get_pipeline_settings()
    with session_scope() as session:
        replace_manga_metrics(
            session,
            compute_manga_metrics(session, settings.smoothing_votes),
            settings.batch_size,
        )
