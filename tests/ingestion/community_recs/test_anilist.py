import json

import httpx
import pytest

from manga_recommender.ingestion.anilist import client as anilist_client
from manga_recommender.ingestion.anilist.client import AnilistClient, AnilistQueryError
from manga_recommender.ingestion.community_recs.anilist import fetch_chunk


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


async def test_fetch_chunk_drops_manga_without_recommendations(monkeypatch):
    media = [
        _media(1, [_node(2, 10)]),
        _media(3, []),
        _media(4, None),
        _media(5, [_node(1, 3), _node(2, 1)]),
    ]
    _patch_transport(monkeypatch, _answer(media))

    async with _client() as client:
        records = await fetch_chunk(client, [1, 3, 4, 5])

    assert [record["id"] for record in records] == [1, 5]


async def test_fetch_chunk_returns_records_exactly_as_anilist_sent_them(monkeypatch):
    # Raw data keeps AniList's field names and nulls. The resolve stage cleans it.
    record = {
        "id": 1,
        "recommendations": {
            "nodes": [
                {"mediaRecommendation": {"id": 2, "type": "MANGA"}, "rating": 7},
                {"mediaRecommendation": None, "rating": 0},
            ]
        },
    }
    _patch_transport(monkeypatch, _answer([record]))

    async with _client() as client:
        assert await fetch_chunk(client, [1]) == [record]


async def test_fetch_chunk_raises_when_the_query_fails(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "boom"}]})

    _patch_transport(monkeypatch, handler)

    async with _client() as client:
        with pytest.raises(AnilistQueryError):
            await fetch_chunk(client, [1])
