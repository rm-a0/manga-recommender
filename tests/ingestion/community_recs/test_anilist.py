import json

import httpx
import pyarrow as pa
import pytest

from manga_recommender.ingestion.anilist import client as anilist_client
from manga_recommender.ingestion.anilist.client import AnilistClient, AnilistQueryError
from manga_recommender.ingestion.community_recs.anilist import (
    EDGE_SCHEMA,
    fetch_chunk,
    to_edges,
)


def _patch_transport(monkeypatch, handler) -> None:
    """Route the AniList client's requests to `handler`."""
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        anilist_client.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )


def _client() -> AnilistClient:
    return AnilistClient(rpm=1_000_000, base_url="https://graphql.anilist.test")


def _media(media_id: int, nodes: list[dict] | None) -> dict:
    recommendations = None if nodes is None else {"nodes": nodes}
    return {"id": media_id, "recommendations": recommendations}


def _node(target_id: int, rating: int) -> dict:
    return {"mediaRecommendation": {"id": target_id, "type": "MANGA"}, "rating": rating}


def _answer(media: list[dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"Page": {"media": media}}})

    return handler


async def test_fetch_chunk_sends_ids_and_per_page(monkeypatch):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["variables"] = json.loads(request.content)["variables"]
        return httpx.Response(200, json={"data": {"Page": {"media": []}}})

    _patch_transport(monkeypatch, handler)

    async with _client() as client:
        await fetch_chunk(client, [30001, 30002, 30003])

    assert captured["variables"] == {"ids": [30001, 30002, 30003], "perPage": 3}


async def test_fetch_chunk_returns_one_row_per_recommendation(monkeypatch):
    media = [_media(1, [_node(2, 10), _node(3, 4)]), _media(5, [_node(1, 3)])]
    _patch_transport(monkeypatch, _answer(media))

    async with _client() as client:
        rows = await fetch_chunk(client, [1, 5])

    assert rows == [
        {"media_id": 1, "recommended_id": 2, "recommended_type": "MANGA", "rating": 10},
        {"media_id": 1, "recommended_id": 3, "recommended_type": "MANGA", "rating": 4},
        {"media_id": 5, "recommended_id": 1, "recommended_type": "MANGA", "rating": 3},
    ]


async def test_fetch_chunk_skips_manga_without_recommendations(monkeypatch):
    media = [_media(1, [_node(2, 10)]), _media(3, []), _media(4, None)]
    _patch_transport(monkeypatch, _answer(media))

    async with _client() as client:
        rows = await fetch_chunk(client, [1, 3, 4])

    assert [row["media_id"] for row in rows] == [1]


def test_to_edges_keeps_every_node_including_negative_ratings_and_deleted_targets():
    media = {
        "id": 1,
        "recommendations": {
            "nodes": [
                {"mediaRecommendation": {"id": 2, "type": "MANGA"}, "rating": -2},
                {"mediaRecommendation": None, "rating": 0},
            ]
        },
    }

    assert to_edges(media) == [
        {"media_id": 1, "recommended_id": 2, "recommended_type": "MANGA", "rating": -2},
        {"media_id": 1, "recommended_id": None, "recommended_type": None, "rating": 0},
    ]


def test_to_edges_rows_fit_the_edge_schema():
    rows = to_edges(_media(1, [_node(2, 10)]))

    table = pa.Table.from_pylist(rows, schema=EDGE_SCHEMA)

    assert table.num_rows == 1


async def test_fetch_chunk_raises_when_the_query_fails(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "boom"}]})

    _patch_transport(monkeypatch, handler)

    async with _client() as client:
        with pytest.raises(AnilistQueryError):
            await fetch_chunk(client, [1])
