"""Fetch AniList community recommendations and land them as one raw run."""

import asyncio
from pathlib import Path

import structlog

from manga_recommender.core.config import get_anilist_settings, get_storage_settings
from manga_recommender.ingestion.anilist.client import AnilistClient
from manga_recommender.ingestion.anilist.paging import (
    get_max_manga_id,
    id_chunks,
    try_fetch_chunk,
)
from manga_recommender.ingestion.community_recs.anilist import fetch_chunk
from manga_recommender.storage.raw import RawRunWriter

logger = structlog.get_logger(__name__)

SOURCE = "anilist"
DATASET = "community_recs"
# Above this share of failed chunks the crawl cannot be trusted. The run then
# gets no manifest, so it never replaces the last complete run.
MAX_FAILED_CHUNK_RATIO = 0.05


async def run_community_recs_ingest() -> None:
    """Fetch the recommendations of every AniList manga and write them to one raw run.

    Record each failed chunk in the manifest. Raise, and write no manifest, when
    more than `MAX_FAILED_CHUNK_RATIO` of the chunks fail.
    """
    settings = get_anilist_settings()
    chunk_size = settings.community_recs_chunk_size
    async with AnilistClient(
        rpm=settings.requests_per_minute, base_url=settings.base_url
    ) as client:
        max_id = settings.max_id or await get_max_manga_id(client)
        logger.info("max_id_resolved", max_id=max_id)
        raw_dir = Path(get_storage_settings().raw_dir)
        with RawRunWriter(raw_dir, SOURCE, DATASET) as run:
            tasks = [
                try_fetch_chunk(fetch_chunk, client, ids)
                for ids in id_chunks(settings.min_id, max_id, chunk_size)
            ]
            failed_chunks: list[list[int]] = []
            for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
                ids, records = await coro
                if records is None:
                    failed_chunks.append([ids[0], ids[-1]])
                    continue
                for record in records:
                    run.write(record)
                logger.info("chunk_fetched", chunk_number=i, total_chunks=len(tasks))

            _check_failed_chunks(len(failed_chunks), len(tasks))
            run.finish(
                failed_chunks=sorted(failed_chunks),
                chunk_size=chunk_size,
                min_id=settings.min_id,
                max_id=max_id,
            )


def _check_failed_chunks(failed: int, total: int) -> None:
    """Log any failed chunks. Raise when they exceed `MAX_FAILED_CHUNK_RATIO`."""
    if not failed:
        return
    logger.warning("chunks_failed", failed=failed, total=total)
    if failed > total * MAX_FAILED_CHUNK_RATIO:
        raise RuntimeError(
            f"{failed} of {total} chunks failed, "
            f"above the {MAX_FAILED_CHUNK_RATIO:.0%} limit. The run is not complete."
        )
