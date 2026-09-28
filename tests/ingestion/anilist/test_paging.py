import asyncio

import httpx
import pytest
import structlog

from manga_recommender.ingestion.anilist import client as anilist_client
from manga_recommender.ingestion.anilist.client import AnilistClient
from manga_recommender.ingestion.anilist.paging import (
    ChunkResult,
    get_max_manga_id,
    id_chunks,
    try_fetch_chunk,
)


def test_id_chunks_splits_range_into_fixed_size_chunks():
    chunks = list(id_chunks(1, 10, 3))

    assert chunks == [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]


def test_id_chunks_returns_single_chunk_when_range_fits():
    chunks = list(id_chunks(5, 7, 10))

    assert chunks == [[5, 6, 7]]


def test_id_chunks_yields_nothing_when_start_is_past_end():
    assert list(id_chunks(10, 9, 3)) == []


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_id_chunks_rejects_chunk_size_below_one(chunk_size):
    with pytest.raises(ValueError):
        list(id_chunks(1, 10, chunk_size))


async def test_get_max_manga_id_returns_highest_media_id(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"Page": {"media": [{"id": 215756}]}}})

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        anilist_client.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )

    async with AnilistClient(
        rpm=1_000_000, base_url="https://graphql.anilist.test"
    ) as client:
        assert await get_max_manga_id(client) == 215756


async def test_try_fetch_chunk_returns_the_records_of_a_successful_chunk():
    async def fetch(client, ids):
        return [{"id": i} for i in ids]

    result = await try_fetch_chunk(fetch, object(), [1, 2])

    assert result == ChunkResult(ids=[1, 2], records=[{"id": 1}, {"id": 2}])


async def test_try_fetch_chunk_returns_none_records_and_logs_when_the_chunk_fails():
    async def fetch(client, ids):
        raise RuntimeError("boom")

    with structlog.testing.capture_logs() as logs:
        ids, records = await try_fetch_chunk(fetch, object(), [30001, 30002, 30025])

    assert (ids, records) == ([30001, 30002, 30025], None)
    assert logs[-1]["event"] == "chunk_failed"
    assert logs[-1]["log_level"] == "warning"
    assert (logs[-1]["first_id"], logs[-1]["last_id"]) == (30001, 30025)


async def test_try_fetch_chunk_does_not_swallow_cancellation():
    async def fetch(client, ids):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await try_fetch_chunk(fetch, object(), [1])
