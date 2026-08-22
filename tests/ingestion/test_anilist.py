import json
from datetime import UTC, datetime

import httpx
import pytest
from aiolimiter import AsyncLimiter

from manga_recommender.config import AniListSettings
from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.ingestion.extractors.anilist import AnilistExtractor


def _extractor(**settings_overrides) -> AnilistExtractor:
    extractor = AnilistExtractor()
    settings_overrides.setdefault("requests_per_minute", 1_000_000)
    extractor.anilist_settings = AniListSettings(**settings_overrides)
    return extractor


def _media(
    *,
    media_id: int = 1,
    mal_id: int | None = 10,
    title: str = "Test Manga",
    description: str | None = "<p>A story about <b>things</b>.</p>",
    start_date: dict | None = None,
    genres: list[str] | None = None,
    status: str = "RELEASING",
    average_score: float | None = 80.0,
    staff_edges: list[dict] | None = None,
    score_distribution: list[dict] | None = None,
) -> dict:
    return {
        "id": media_id,
        "idMal": mal_id,
        "title": {"romaji": title},
        "description": description,
        "startDate": start_date,
        "genres": genres if genres is not None else ["Action"],
        "status": status,
        "averageScore": average_score,
        "staff": {
            "edges": staff_edges
            if staff_edges is not None
            else [{"role": "Story & Art", "node": {"name": {"full": "Author One"}}}]
        },
        "stats": {
            "scoreDistribution": score_distribution
            if score_distribution is not None
            else [{"score": 10, "amount": 3}, {"score": 90, "amount": 7}]
        },
    }


def test_extract_author_joins_story_and_art_staff():
    extractor = _extractor()
    media = _media(
        staff_edges=[
            {"role": "Story", "node": {"name": {"full": "Writer A"}}},
            {"role": "Art", "node": {"name": {"full": "Artist B"}}},
            {"role": "Character Design", "node": {"name": {"full": "Someone Else"}}},
        ]
    )

    assert extractor._extract_author(media) == "Writer A, Artist B"


def test_extract_author_returns_unknown_when_no_story_or_art_staff():
    extractor = _extractor()
    media = _media(staff_edges=[{"role": "Producer", "node": {"name": {"full": "P"}}}])

    assert extractor._extract_author(media) == "Unknown"


def test_extract_status_maps_known_status():
    extractor = _extractor()

    assert extractor._extract_status(_media(status="FINISHED")) == MangaStatus.FINISHED


def test_extract_status_returns_none_for_unmapped_status():
    extractor = _extractor()

    assert extractor._extract_status(_media(status="TBA")) is None


def test_extract_votes_count_sums_distribution_amounts():
    extractor = _extractor()
    media = _media(score_distribution=[{"amount": 2}, {"amount": 5}, {"amount": 1}])

    assert extractor._extract_votes_count(media) == 8


def test_extract_votes_count_returns_none_when_no_distribution():
    extractor = _extractor()
    media = _media(score_distribution=[])

    assert extractor._extract_votes_count(media) is None


def test_extract_score_distribution_maps_scores_to_buckets():
    extractor = _extractor()
    media = _media(
        score_distribution=[
            {"score": 10, "amount": 2},
            {"score": 50, "amount": 5},
            {"score": 100, "amount": 1},
        ]
    )

    assert extractor._extract_score_distribution(media) == [
        2,
        0,
        0,
        0,
        5,
        0,
        0,
        0,
        0,
        1,
    ]


def test_extract_score_distribution_returns_none_when_no_distribution():
    extractor = _extractor()
    media = _media(score_distribution=[])

    assert extractor._extract_score_distribution(media) is None


def test_extract_description_strips_html_tags():
    extractor = _extractor()
    media = _media(description="<p>A story about <b>things</b>.</p>")

    assert extractor._extract_description(media) == "A story about things."


def test_extract_description_returns_none_when_missing():
    extractor = _extractor()
    media = _media(description=None)

    assert extractor._extract_description(media) is None


def test_extract_published_date_uses_full_start_date():
    extractor = _extractor()
    media = _media(start_date={"year": 1997, "month": 8, "day": 1})

    assert extractor._extract_published_date(media) == datetime(1997, 8, 1, tzinfo=UTC)


def test_extract_published_date_defaults_missing_month_and_day_to_one():
    extractor = _extractor()
    media = _media(start_date={"year": 1985, "month": None, "day": None})

    assert extractor._extract_published_date(media) == datetime(1985, 1, 1, tzinfo=UTC)


def test_extract_published_date_returns_none_when_year_missing():
    extractor = _extractor()
    media = _media(start_date={"year": None, "month": None, "day": None})

    assert extractor._extract_published_date(media) is None


def test_extract_published_date_returns_none_when_start_date_missing():
    extractor = _extractor()
    media = _media(start_date=None)

    assert extractor._extract_published_date(media) is None


def test_to_record_converts_media_to_normalized_record():
    extractor = _extractor()
    media = _media(
        media_id=42,
        mal_id=100,
        title="Vagabond",
        genres=["Action", "Drama"],
        average_score=91.0,
    )

    record = extractor._to_record(media)

    assert record.external_id == "42"
    assert record.mal_id == 100
    assert record.title == "Vagabond"
    assert record.author == "Author One"
    assert record.status == MangaStatus.ONGOING
    assert record.genres == ["Action", "Drama"]
    assert record.raw_score == 91.0
    assert record.raw_scale_max == 100.0
    assert record.votes_count == 10
    assert record.score_distribution == [3, 0, 0, 0, 0, 0, 0, 0, 7, 0]
    assert record.published_date is None
    assert record.description == "A story about things."
    assert record.fetched_at is not None


def test_id_chunks_splits_range_into_fixed_size_chunks():
    extractor = _extractor()

    chunks = list(extractor._id_chunks(1, 10, 3))

    assert chunks == [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10]]


def test_id_chunks_returns_single_chunk_when_range_fits():
    extractor = _extractor()

    chunks = list(extractor._id_chunks(5, 7, 10))

    assert chunks == [[5, 6, 7]]


def test_parse_response_returns_body_on_success():
    extractor = _extractor()
    response = httpx.Response(
        200, json={"data": {"ok": True}}, request=httpx.Request("POST", "https://test")
    )

    assert extractor._parse_response(response) == {"data": {"ok": True}}


def test_parse_response_raises_on_http_error():
    extractor = _extractor()
    response = httpx.Response(500, request=httpx.Request("POST", "https://test"))

    with pytest.raises(httpx.HTTPStatusError):
        extractor._parse_response(response)


def test_parse_response_raises_on_graphql_errors():
    extractor = _extractor()
    response = httpx.Response(
        200,
        json={"errors": [{"message": "boom"}]},
        request=httpx.Request("POST", "https://test"),
    )

    with pytest.raises(RuntimeError):
        extractor._parse_response(response)


def test_get_max_id_returns_highest_media_id(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"Page": {"media": [{"id": 215756}]}}})

    real_client = httpx.Client
    monkeypatch.setattr(
        "manga_recommender.ingestion.extractors.anilist.httpx.Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    extractor = _extractor()

    assert extractor._get_max_id() == 215756


async def test_fetch_chunk_sends_ids_and_per_page():
    extractor = _extractor()
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["variables"] = json.loads(request.content)["variables"]
        return httpx.Response(200, json={"data": {"Page": {"media": []}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await extractor._fetch_chunk(client, AsyncLimiter(1000, 1), [30001, 30002])

    assert captured["variables"] == {"ids": [30001, 30002], "perPage": 2}


async def test_fetch_chunk_returns_media_list():
    extractor = _extractor()
    media = [{"id": 1}, {"id": 2}]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"Page": {"media": media}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await extractor._fetch_chunk(client, AsyncLimiter(1000, 1), [1, 2])

    assert result == media


async def test_fetch_chunk_raises_on_graphql_errors():
    extractor = _extractor()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "boom"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError):
            await extractor._fetch_chunk(client, AsyncLimiter(1000, 1), [1])


async def test_fetch_chunk_retries_after_429(monkeypatch):
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "manga_recommender.ingestion.extractors.anilist.asyncio.sleep", fake_sleep
    )
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "5"}),
            httpx.Response(200, json={"data": {"Page": {"media": []}}}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    extractor = _extractor()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await extractor._fetch_chunk(client, AsyncLimiter(1000, 1), [1])

    assert result == []
    assert sleep_calls == [5]


def test_extract_yields_records_for_each_media(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        ids = json.loads(request.content)["variables"]["ids"]
        media = [_media(media_id=i) for i in ids]
        return httpx.Response(200, json={"data": {"Page": {"media": media}}})

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "manga_recommender.ingestion.extractors.anilist.httpx.AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(handler), **kwargs
        ),
    )

    extractor = _extractor(min_id=1, max_id=3, chunk_size=2)
    records = list(extractor.extract())

    assert sorted(record.external_id for record in records) == ["1", "2", "3"]


def test_extract_resolves_max_id_when_not_configured(monkeypatch):
    def sync_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"Page": {"media": [{"id": 30002}]}}})

    def async_handler(request: httpx.Request) -> httpx.Response:
        ids = json.loads(request.content)["variables"]["ids"]
        media = [_media(media_id=i) for i in ids]
        return httpx.Response(200, json={"data": {"Page": {"media": media}}})

    real_client = httpx.Client
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "manga_recommender.ingestion.extractors.anilist.httpx.Client",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(sync_handler), **kwargs
        ),
    )
    monkeypatch.setattr(
        "manga_recommender.ingestion.extractors.anilist.httpx.AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(async_handler), **kwargs
        ),
    )

    extractor = _extractor(min_id=30001, max_id=None, chunk_size=50)
    records = list(extractor.extract())

    assert sorted(record.external_id for record in records) == ["30001", "30002"]


def test_extract_skips_max_id_lookup_when_configured(monkeypatch):
    def async_handler(request: httpx.Request) -> httpx.Response:
        ids = json.loads(request.content)["variables"]["ids"]
        media = [_media(media_id=i) for i in ids]
        return httpx.Response(200, json={"data": {"Page": {"media": media}}})

    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "manga_recommender.ingestion.extractors.anilist.httpx.AsyncClient",
        lambda **kwargs: real_async_client(
            transport=httpx.MockTransport(async_handler), **kwargs
        ),
    )

    extractor = _extractor(min_id=1, max_id=2, chunk_size=50)

    def _fail_if_called() -> int:
        raise AssertionError("_get_max_id should not be called when max_id is set")

    monkeypatch.setattr(extractor, "_get_max_id", _fail_if_called)

    records = list(extractor.extract())

    assert sorted(record.external_id for record in records) == ["1", "2"]
