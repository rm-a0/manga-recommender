import json

import httpx
import pytest

from manga_recommender.core.config import AnilistSettings, StorageSettings
from manga_recommender.ingestion.anilist import client as anilist_client
from manga_recommender.ingestion.community_recs import runner
from manga_recommender.storage.raw import (
    latest_complete_run,
    read_manifest,
    read_records,
)

BASE_URL = "https://graphql.anilist.test"


def _configure(monkeypatch, tmp_path, *, max_id: int | None, chunk_size: int = 2):
    settings = AnilistSettings(
        base_url=BASE_URL,
        requests_per_minute=1_000_000,
        min_id=1,
        max_id=max_id,
        community_recs_chunk_size=chunk_size,
    )
    monkeypatch.setattr(runner, "get_anilist_settings", lambda: settings)
    monkeypatch.setattr(
        runner,
        "get_storage_settings",
        lambda: StorageSettings(community_recs_path=tmp_path),
    )


def _serve(monkeypatch, *, max_id: int = 0, without_recs=(), failing=()):
    """Answer AniList queries. `failing` IDs make their whole chunk fail."""

    def handler(request: httpx.Request) -> httpx.Response:
        variables = json.loads(request.content)["variables"]
        if variables is None:
            media = [{"id": max_id}]
            return httpx.Response(200, json={"data": {"Page": {"media": media}}})
        ids = variables["ids"]
        if any(i in failing for i in ids):
            return httpx.Response(200, json={"errors": [{"message": "boom"}]})
        media = [
            {
                "id": i,
                "recommendations": {
                    "nodes": []
                    if i in without_recs
                    else [
                        {
                            "mediaRecommendation": {"id": i + 1, "type": "MANGA"},
                            "rating": i,
                        }
                    ]
                },
            }
            for i in ids
        ]
        return httpx.Response(200, json={"data": {"Page": {"media": media}}})

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        anilist_client.httpx,
        "AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )


def _complete_run(tmp_path):
    return latest_complete_run(tmp_path)


async def test_ingest_writes_each_manga_with_recommendations_and_finishes(
    monkeypatch, tmp_path
):
    _configure(monkeypatch, tmp_path, max_id=5)
    _serve(monkeypatch, without_recs={2})

    await runner.run_community_recs_ingest()

    run_dir = _complete_run(tmp_path)
    assert sorted(record["id"] for record in read_records(run_dir)) == [1, 3, 4, 5]
    manifest = read_manifest(run_dir)
    assert manifest["failed_chunks"] == []
    assert (manifest["chunk_size"], manifest["min_id"], manifest["max_id"]) == (2, 1, 5)
    assert manifest["record_count"] == 4


async def test_ingest_resolves_max_id_when_not_configured(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path, max_id=None)
    _serve(monkeypatch, max_id=3)

    await runner.run_community_recs_ingest()

    run_dir = _complete_run(tmp_path)
    assert read_manifest(run_dir)["max_id"] == 3
    assert sorted(record["id"] for record in read_records(run_dir)) == [1, 2, 3]


async def test_a_few_failed_chunks_are_recorded_and_the_run_still_finishes(
    monkeypatch, tmp_path
):
    # 1 of 20 chunks fails: exactly the 5% limit.
    _configure(monkeypatch, tmp_path, max_id=40)
    _serve(monkeypatch, failing={3})

    await runner.run_community_recs_ingest()

    run_dir = _complete_run(tmp_path)
    assert read_manifest(run_dir)["failed_chunks"] == [[3, 4]]
    ids = {record["id"] for record in read_records(run_dir)}
    assert ids == set(range(1, 41)) - {3, 4}


async def test_too_many_failed_chunks_raise_and_leave_no_complete_run(
    monkeypatch, tmp_path
):
    # 1 of 2 chunks fails: above the limit.
    _configure(monkeypatch, tmp_path, max_id=4)
    _serve(monkeypatch, failing={3})

    with pytest.raises(RuntimeError, match="1 of 2 chunks failed"):
        await runner.run_community_recs_ingest()

    with pytest.raises(FileNotFoundError):
        _complete_run(tmp_path)
