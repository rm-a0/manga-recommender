import json

import httpx
import pyarrow as pa
import pytest
import structlog

from manga_recommender.core import storage
from manga_recommender.core.config import AnilistSettings, StorageSettings
from manga_recommender.ingestion.anilist import client as anilist_client
from manga_recommender.ingestion.community_recs import runner
from manga_recommender.ingestion.community_recs.anilist import EDGE_SCHEMA

BASE_URL = "https://graphql.anilist.test"


def _configure(monkeypatch, path, *, max_id: int | None, chunk_size: int = 2):
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
        lambda: StorageSettings(community_recs_path=path),
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


@pytest.fixture
def artifact_path(tmp_path):
    return tmp_path / "artifacts" / "community_recs.parquet"


def _rows(path):
    return storage.read_table(path).to_pylist()


async def test_ingest_writes_one_row_per_recommendation(monkeypatch, artifact_path):
    _configure(monkeypatch, artifact_path, max_id=5)
    _serve(monkeypatch, without_recs={2})

    await runner.run_community_recs_ingest()

    rows = sorted(_rows(artifact_path), key=lambda row: row["media_id"])
    assert [row["media_id"] for row in rows] == [1, 3, 4, 5]
    assert rows[0] == {
        "media_id": 1,
        "recommended_id": 2,
        "recommended_type": "MANGA",
        "rating": 1,
    }


async def test_ingest_resolves_max_id_when_not_configured(monkeypatch, artifact_path):
    _configure(monkeypatch, artifact_path, max_id=None)
    _serve(monkeypatch, max_id=3)

    await runner.run_community_recs_ingest()

    assert sorted(row["media_id"] for row in _rows(artifact_path)) == [1, 2, 3]


async def test_a_few_failed_chunks_are_logged_and_the_file_is_still_written(
    monkeypatch, artifact_path
):
    # 1 of 20 chunks fails: exactly the 5% limit.
    _configure(monkeypatch, artifact_path, max_id=40)
    _serve(monkeypatch, failing={3})

    with structlog.testing.capture_logs() as logs:
        await runner.run_community_recs_ingest()

    assert {row["media_id"] for row in _rows(artifact_path)} == set(range(1, 41)) - {
        3,
        4,
    }
    failed = [log for log in logs if log["event"] == "chunks_failed"]
    assert failed[0]["chunks"] == [[3, 4]]


async def test_too_many_failed_chunks_raise_and_keep_the_previous_file(
    monkeypatch, artifact_path
):
    # 1 of 2 chunks fails: above the limit.
    storage.write_table(artifact_path, pa.Table.from_pylist([], schema=EDGE_SCHEMA))
    original = artifact_path.read_bytes()
    _configure(monkeypatch, artifact_path, max_id=4)
    _serve(monkeypatch, failing={3})

    with pytest.raises(RuntimeError, match="1 of 2 chunks failed"):
        await runner.run_community_recs_ingest()

    assert artifact_path.read_bytes() == original
