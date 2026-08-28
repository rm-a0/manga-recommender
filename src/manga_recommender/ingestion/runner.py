"""Seed sources, batch extractor output, and load it into the database."""

import itertools
import time
import uuid

import structlog

from manga_recommender.db.repositories.manga import delete_orphaned_manga
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


def prune_orphaned_manga() -> int:
    """Delete manga left without any external rating, and return how many went."""
    with session_scope() as session:
        return delete_orphaned_manga(session)


def run_ingestion(sources: list[str], batch_size: int) -> None:
    """Run the ingestion pipeline for the given list of source names.

    Logs and continues on failure, at both the batch and the source level.
    """
    genre_cache: dict[str, uuid.UUID] = {}
    author_cache: dict[str, uuid.UUID] = {}
    for source in sources:
        try:
            logger.info("ingestion_started", source=source)
            source_id = seed_source(source)
            extractor = get_extractor_for_source(source)
            for batch in itertools.batched(extractor.extract(), batch_size):
                start_time = time.monotonic()
                try:
                    load_batch(batch, source_id, genre_cache, author_cache)
                except Exception:
                    # One bad batch must not end the source's whole run.
                    logger.exception("batch_failed", source=source, count=len(batch))
                    continue
                logger.info(
                    "batch_loaded",
                    source=source,
                    count=len(batch),
                    elapsed_s=round(time.monotonic() - start_time, 1),
                )
            logger.info("ingestion_completed", source=source)
        except Exception:
            logger.exception("ingestion_failed", source=source)

    try:
        logger.info("orphans_pruned", count=prune_orphaned_manga())
    except Exception:
        logger.exception("orphan_prune_failed")
