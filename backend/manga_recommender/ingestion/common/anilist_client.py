"""Client that sends GraphQL queries to AniList under its rate limit."""

from types import TracebackType
from typing import Final, Self

import httpx
import structlog
from aiolimiter import AsyncLimiter
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

DEFAULT_RETRY_AFTER_S: Final[float] = 60.0
_BACKOFF: Final = wait_exponential(multiplier=2)


class AnilistError(Exception):
    """Base class for the errors that the AniList client raises."""


class AnilistQueryError(AnilistError):
    """AniList rejected the query. A retry cannot fix it."""


class AnilistServerError(AnilistError):
    """AniList answered with a 5xx status."""


class AnilistRateLimitError(AnilistError):
    """AniList answered with 429."""

    def __init__(self, retry_after: float) -> None:
        """Keep the wait that AniList asked for."""
        super().__init__(f"AniList rate limit hit, retry after {retry_after} s")
        self.retry_after = retry_after


_RETRYABLE: Final = (httpx.TransportError, AnilistServerError, AnilistRateLimitError)


class AnilistClient:
    """Send GraphQL queries to AniList. Retry the failures that can recover.

    One instance holds the rate limiter. Use one instance for each run, because
    AniList counts requests for each IP address.
    """

    def __init__(
        self,
        rpm: int,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Create the rate limiter and the HTTP client."""
        self._base_url = base_url
        self._max_retries = max_retries
        self.rate_limiter = AsyncLimiter(1, 60 / rpm)
        self.http_client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self) -> Self:
        """Open the HTTP client and return this client."""
        await self.http_client.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Close the HTTP connection pool."""
        await self.http_client.__aexit__(exc_type, exc, tb)

    async def execute(self, query: str, variables: dict | None = None) -> dict:
        """Send a GraphQL query and return its `data` object.

        `max_retries` counts all attempts, including the attempts after a 429.
        """
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=self._retry_wait,
            retry=retry_if_exception_type(_RETRYABLE),
            before_sleep=self._log_retry,
            reraise=True,
        )
        return await retrying(self._post_query, query, variables)

    async def _post_query(self, query: str, variables: dict | None) -> dict:
        """Send one request and return its `data`, or raise a typed error."""
        async with self.rate_limiter:
            response = await self.http_client.post(
                self._base_url,
                json={"query": query, "variables": variables},
            )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", DEFAULT_RETRY_AFTER_S)
            raise AnilistRateLimitError(float(retry_after))
        if response.is_server_error:
            raise AnilistServerError(f"AniList returned HTTP {response.status_code}")

        try:
            body = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        if body.get("errors"):
            raise AnilistQueryError(f"AniList query failed: {body['errors']}")
        response.raise_for_status()
        return body["data"]

    def _retry_wait(self, retry_state: RetryCallState) -> float:
        """Return the wait before the next attempt.

        A 429 uses the wait that AniList asked for. Other errors wait 2 s, then
        4 s, then 8 s.
        """
        error = retry_state.outcome.exception() if retry_state.outcome else None
        if isinstance(error, AnilistRateLimitError):
            return error.retry_after
        return _BACKOFF(retry_state)

    def _log_retry(self, retry_state: RetryCallState) -> None:
        """Log the failed attempt and the wait before the next one."""
        error = retry_state.outcome.exception() if retry_state.outcome else None
        logger.warning(
            "request_retrying",
            attempt=retry_state.attempt_number,
            error=type(error).__name__,
            detail=str(error),
            wait_s=retry_state.upcoming_sleep,
        )
