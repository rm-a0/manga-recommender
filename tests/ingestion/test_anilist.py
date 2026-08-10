import json

import httpx
import pytest

from manga_recommender.config import AniListSettings
from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.ingestion.anilist import AnilistExtractor


def _extractor(**settings_overrides) -> AnilistExtractor:
    extractor = AnilistExtractor()
    extractor.anilist_settings = AniListSettings(request_delay=0, **settings_overrides)
    return extractor


def _media(
    *,
    media_id: int = 1,
    mal_id: int | None = 10,
    title: str = "Test Manga",
    description: str | None = "<p>A story about <b>things</b>.</p>",
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
            else [{"amount": 3}, {"amount": 7}]
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


def test_extract_description_strips_html_tags():
    extractor = _extractor()
    media = _media(description="<p>A story about <b>things</b>.</p>")

    assert extractor._extract_description(media) == "A story about things."


def test_extract_description_returns_none_when_missing():
    extractor = _extractor()
    media = _media(description=None)

    assert extractor._extract_description(media) is None


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
    assert record.published_date is None
    assert record.description == "A story about things."
    assert record.fetched_at is not None


def test_fetch_page_returns_parsed_response_body():
    extractor = _extractor()
    body = {"data": {"Page": {"pageInfo": {"hasNextPage": False}, "media": []}}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert extractor._fetch_page(client, 1) == body


def test_fetch_page_sends_id_greater_and_per_page_variables():
    extractor = _extractor(per_page=25)
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["variables"] = json.loads(request.content)["variables"]
        return httpx.Response(
            200,
            json={"data": {"Page": {"pageInfo": {"hasNextPage": False}, "media": []}}},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        extractor._fetch_page(client, 42)

    assert captured["variables"] == {"perPage": 25, "idGreater": 42}


def test_fetch_page_raises_on_graphql_errors():
    extractor = _extractor()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "boom"}]})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(RuntimeError),
    ):
        extractor._fetch_page(client, 1)


def test_fetch_page_retries_after_429(monkeypatch):
    monkeypatch.setattr(
        "manga_recommender.ingestion.anilist.time.sleep", lambda _: None
    )
    extractor = _extractor()
    responses = iter(
        [
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(
                200,
                json={
                    "data": {"Page": {"pageInfo": {"hasNextPage": False}, "media": []}}
                },
            ),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        body = extractor._fetch_page(client, 1)

    assert body["data"]["Page"]["media"] == []


def test_extract_yields_records_across_pages(monkeypatch):
    pages = iter(
        [
            {
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": True},
                        "media": [_media(media_id=1, title="Manga A")],
                    }
                }
            },
            {
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": False},
                        "media": [_media(media_id=2, title="Manga B")],
                    }
                }
            },
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=next(pages))

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        "manga_recommender.ingestion.anilist.httpx.Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )

    extractor = _extractor()
    titles = [record.title for record in extractor.extract()]

    assert titles == ["Manga A", "Manga B"]


def test_extract_advances_cursor_using_max_id_seen(monkeypatch):
    pages = iter(
        [
            {
                "data": {
                    "Page": {
                        "pageInfo": {"hasNextPage": True},
                        "media": [_media(media_id=5), _media(media_id=8)],
                    }
                }
            },
            {"data": {"Page": {"pageInfo": {"hasNextPage": False}, "media": []}}},
        ]
    )
    id_greater_seen: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        id_greater_seen.append(json.loads(request.content)["variables"]["idGreater"])
        return httpx.Response(200, json=next(pages))

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        "manga_recommender.ingestion.anilist.httpx.Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )

    extractor = _extractor()
    list(extractor.extract())

    assert id_greater_seen == [0, 8]


def test_extract_stops_when_media_is_empty(monkeypatch):
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            json={"data": {"Page": {"pageInfo": {"hasNextPage": True}, "media": []}}},
        )

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(
        "manga_recommender.ingestion.anilist.httpx.Client",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )

    extractor = _extractor()
    records = list(extractor.extract())

    assert records == []
    assert request_count == 1
