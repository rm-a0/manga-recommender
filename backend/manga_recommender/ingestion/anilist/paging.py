"""Walk every AniList manga ID in fixed-size chunks.

Ingests query each chunk with `id_in`. This avoids AniList's page-based
pagination, which stops at 5,000 results.
"""

from collections.abc import Awaitable, Callable, Iterator
from itertools import batched
from typing import Any, NamedTuple

import structlog

from manga_recommender.ingestion.anilist.client import AnilistClient

logger = structlog.get_logger(__name__)

ChunkFetcher = Callable[[AnilistClient, list[int]], Awaitable[list[dict[str, Any]]]]

MAX_MANGA_ID_QUERY = """
query {
    Page(page: 1, perPage: 1) {
        media(type: MANGA, sort: ID_DESC) { id }
    }
}
"""


async def get_max_manga_id(client: AnilistClient) -> int:
    """Return the highest manga ID on AniList."""
    data = await client.execute(MAX_MANGA_ID_QUERY)
    return data["Page"]["media"][0]["id"]


def id_chunks(start_id: int, end_id: int, chunk_size: int) -> Iterator[list[int]]:
    """Yield consecutive lists of IDs from `start_id` to `end_id`, both included.

    Raise `ValueError` when `chunk_size` is less than 1.
    """
    for chunk in batched(range(start_id, end_id + 1), chunk_size, strict=False):
        yield list(chunk)


class ChunkResult(NamedTuple):
    """The records of one chunk, or None when the chunk failed."""

    ids: list[int]
    records: list[dict[str, Any]] | None


async def try_fetch_chunk(
    fetch: ChunkFetcher,
    client: AnilistClient,
    ids: list[int],
) -> ChunkResult:
    """Run `fetch` for one chunk. Log a failure and return it instead of raising.

    One failed chunk must not end a crawl. The caller records `ids` as failed.
    """
    try:
        return ChunkResult(ids, await fetch(client, ids))
    except Exception:
        logger.warning("chunk_failed", first_id=ids[0], last_id=ids[-1], exc_info=True)
        return ChunkResult(ids, None)
