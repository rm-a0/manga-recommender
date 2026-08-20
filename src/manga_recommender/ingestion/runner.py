"""Seed sources, batch extractor output, and load it into the database."""

import itertools
import time
import uuid

import structlog

from manga_recommender.db.repositories.sources import get_or_create_source
from manga_recommender.db.session import session_scope
from manga_recommender.ingestion.loader import load_batch
from manga_recommender.ingestion.registry import (
    get_extractor_for_source,
    get_source_weight,
)

logger = structlog.get_logger(__name__)


def seed_source(source_name: str) -> uuid.UUID:
    """Ensure that the given source is present in the database, creating it if needed."""
    with session_scope() as session:
        return get_or_create_source(
            session,
            name=source_name,
            weight=get_source_weight(source_name),
        ).id


def run_ingestion(sources: list[str], batch_size: int) -> None:
    """Run the ingestion pipeline for the given list of source names.

    Logs and continues with the next source if one fails.
    """
    for source in sources:
        try:
            logger.info("ingestion_started", source=source)
            source_id = seed_source(source)
            extractor = get_extractor_for_source(source)
            for batch in itertools.batched(extractor.extract(), batch_size):
                batch = batch
                start_time = time.monotonic()
                load_batch(batch, source_id)
                logger.info(
                    "batch_loaded",
                    source=source,
                    count=len(batch),
                    elapsed_s=round(time.monotonic() - start_time, 1),
                )
        except Exception:
            logger.exception("ingestion_failed", source=source)
        logger.info("ingestion_completed", source=source)
