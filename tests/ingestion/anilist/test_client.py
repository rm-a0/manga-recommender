import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from manga_recommender.ingestion.anilist import client as anilist_client
from manga_recommender.ingestion.anilist.client import (
    AnilistClient,
    AnilistQueryError,
    AnilistRateLimitError,
    AnilistServerError,
)

BASE_URL = "https://graphql.anilist.test"
QUERY = "query { Page { media { id } } }"
DATA = {"Page": {"media": [{"id": 1}]}}

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    """Record each retry wait instead of sleeping."""
    calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return calls


@pytest.fixture
def make_client(monkeypatch) -> Callable[..., AnilistClient]:
    """Return a factory for clients that answer through a mock transport."""
    real_async_client = httpx.AsyncClient

    def factory(handler: Handler, max_retries: int = 3) -> AnilistClient:
        monkeypatch.setattr(
            anilist_client.httpx,
            "AsyncClient",
            lambda **kwargs: real_async_client(
                transport=httpx.MockTransport(handler), **kwargs
            ),
        )
        return AnilistClient(rpm=60_000, base_url=BASE_URL, max_retries=max_retries)

    return factory


class Replay:
    """Answer each request with the next response, and count the requests.

    The last response repeats, so a test can model a lasting failure.
    """

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = (
            self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        )
        if isinstance(response, Exception):
            raise response
        return response


def _ok(data: dict = DATA) -> httpx.Response:
    return httpx.Response(200, json={"data": data})


async def test_execute_returns_the_data_object(make_client):
    async with make_client(Replay(_ok())) as client:
        assert await client.execute(QUERY) == DATA


async def test_execute_posts_the_query_and_variables(make_client):
    replay = Replay(_ok())

    async with make_client(replay) as client:
        await client.execute(QUERY, {"ids": [1, 2], "perPage": 2})

    request = replay.requests[0]
    assert request.method == "POST"
    assert str(request.url) == BASE_URL
    assert json.loads(request.content) == {
        "query": QUERY,
        "variables": {"ids": [1, 2], "perPage": 2},
    }


async def test_graphql_errors_raise_a_query_error_without_retry(make_client, sleeps):
    replay = Replay(httpx.Response(200, json={"errors": [{"message": "boom"}]}))

    async with make_client(replay) as client:
        with pytest.raises(AnilistQueryError, match="boom"):
            await client.execute(QUERY)

    assert len(replay.requests) == 1
    assert sleeps == []


async def test_a_4xx_with_graphql_errors_keeps_the_anilist_message(make_client):
    replay = Replay(
        httpx.Response(400, json={"errors": [{"message": "Invalid field"}]})
    )

    async with make_client(replay) as client:
        with pytest.raises(AnilistQueryError, match="Invalid field"):
            await client.execute(QUERY)


async def test_a_4xx_without_a_json_body_raises_the_status_error(make_client, sleeps):
    replay = Replay(httpx.Response(404, text="Not Found"))

    async with make_client(replay) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.execute(QUERY)

    assert len(replay.requests) == 1
    assert sleeps == []


async def test_a_429_waits_for_retry_after_then_retries(make_client, sleeps):
    replay = Replay(httpx.Response(429, headers={"Retry-After": "5"}), _ok())

    async with make_client(replay) as client:
        assert await client.execute(QUERY) == DATA

    assert sleeps == [5.0]


async def test_a_429_without_retry_after_waits_the_default(make_client, sleeps):
    replay = Replay(httpx.Response(429), _ok())

    async with make_client(replay) as client:
        await client.execute(QUERY)

    assert sleeps == [anilist_client.DEFAULT_RETRY_AFTER_S]


async def test_repeated_429s_stop_at_max_retries(make_client, sleeps):
    replay = Replay(httpx.Response(429, headers={"Retry-After": "1"}))

    async with make_client(replay, max_retries=3) as client:
        with pytest.raises(AnilistRateLimitError):
            await client.execute(QUERY)

    assert len(replay.requests) == 3
    assert sleeps == [1.0, 1.0]


async def test_a_5xx_backs_off_then_retries(make_client, sleeps):
    replay = Replay(httpx.Response(503), _ok())

    async with make_client(replay) as client:
        assert await client.execute(QUERY) == DATA

    assert sleeps == [2.0]


async def test_a_lasting_5xx_raises_a_server_error_after_max_retries(
    make_client, sleeps
):
    replay = Replay(httpx.Response(502))

    async with make_client(replay, max_retries=3) as client:
        with pytest.raises(AnilistServerError, match="502"):
            await client.execute(QUERY)

    assert len(replay.requests) == 3
    assert sleeps == [2.0, 4.0]


async def test_a_transport_error_is_retried(make_client, sleeps):
    replay = Replay(httpx.ConnectError("refused"), _ok())

    async with make_client(replay) as client:
        assert await client.execute(QUERY) == DATA

    assert len(replay.requests) == 2


async def test_a_lasting_transport_error_is_reraised(make_client, sleeps):
    replay = Replay(httpx.ConnectError("refused"))

    async with make_client(replay, max_retries=2) as client:
        with pytest.raises(httpx.ConnectError):
            await client.execute(QUERY)

    assert len(replay.requests) == 2


async def test_leaving_the_context_closes_the_http_client(make_client):
    client = make_client(Replay(_ok()))

    async with client:
        pass

    with pytest.raises(RuntimeError, match="closed"):
        await client.execute(QUERY)


async def test_concurrent_calls_keep_separate_retry_state(make_client, sleeps):
    """One call's failures must not count toward another call's attempts."""
    responses = {
        "flaky": iter([httpx.Response(503), httpx.Response(503), _ok({"a": 1})]),
        "steady": iter([_ok({"b": 2})]),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses[json.loads(request.content)["variables"]["name"]])

    async with make_client(handler, max_retries=3) as client:
        flaky, steady = await asyncio.gather(
            client.execute(QUERY, {"name": "flaky"}),
            client.execute(QUERY, {"name": "steady"}),
        )

    assert flaky == {"a": 1}
    assert steady == {"b": 2}
