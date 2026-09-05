"""Recompute the derived rating metrics for every manga."""

from collections.abc import Sequence

import structlog
from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga_metrics import (
    MetricValues,
    bulk_create_manga_metrics,
    delete_all_manga_metrics,
)

logger = structlog.get_logger(__name__)


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
    db.commit()
