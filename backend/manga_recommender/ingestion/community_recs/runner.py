"""Fetch AniList community recommendations and write them to one Parquet artifact."""

import asyncio
from typing import Any

import pyarrow as pa
import structlog

from manga_recommender.core import storage
from manga_recommender.core.config import get_anilist_settings, get_storage_settings
from manga_recommender.ingestion.anilist.client import AnilistClient
from manga_recommender.ingestion.anilist.paging import (
    get_max_manga_id,
    id_chunks,
    try_fetch_chunk,
)
from manga_recommender.ingestion.community_recs.anilist import EDGE_SCHEMA, fetch_chunk

logger = structlog.get_logger(__name__)

MAX_FAILED_CHUNK_RATIO = 0.05


async def run_community_recs_ingest() -> None:
    """Fetch the recommendations of every AniList manga and write the artifact.

    Raise, and keep the previous artifact, when more than `MAX_FAILED_CHUNK_RATIO`
    of the chunks fail.
    """
    settings = get_anilist_settings()
    path = get_storage_settings().community_recs_path
    async with AnilistClient(
        rpm=settings.requests_per_minute, base_url=settings.base_url
    ) as client:
        max_id = settings.max_id or await get_max_manga_id(client)
        logger.info("max_id_resolved", max_id=max_id)
        tasks = [
            try_fetch_chunk(fetch_chunk, client, ids)
            for ids in id_chunks(
                settings.min_id, max_id, settings.community_recs_chunk_size
            )
        ]
        rows: list[dict[str, Any]] = []
        failed_chunks: list[list[int]] = []
        for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
            ids, chunk_rows = await coro
            if chunk_rows is None:
                failed_chunks.append([ids[0], ids[-1]])
                continue
            rows.extend(chunk_rows)
            logger.info("chunk_fetched", chunk_number=i, total_chunks=len(tasks))

    _check_failed_chunks(sorted(failed_chunks), len(tasks))
    storage.write_table(path, pa.Table.from_pylist(rows, schema=EDGE_SCHEMA))
    logger.info("community_recs_written", path=str(path), rows=len(rows))


def _check_failed_chunks(failed_chunks: list[list[int]], total: int) -> None:
    """Log any failed chunks. Raise when they exceed `MAX_FAILED_CHUNK_RATIO`."""
    if not failed_chunks:
        return
    logger.warning(
        "chunks_failed", failed=len(failed_chunks), total=total, chunks=failed_chunks
    )
    if len(failed_chunks) > total * MAX_FAILED_CHUNK_RATIO:
        raise RuntimeError(
            f"{len(failed_chunks)} of {total} chunks failed, "
            f"above the {MAX_FAILED_CHUNK_RATIO:.0%} limit. Nothing was written."
        )
