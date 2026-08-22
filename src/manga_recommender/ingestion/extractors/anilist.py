"""Extractor that pulls manga data from the AniList GraphQL API."""

import asyncio
import re
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime

import httpx
import structlog
from aiolimiter import AsyncLimiter

from manga_recommender.config import get_anilist_settings
from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.ingestion.base import BaseExtractor, NormalizedMangaRecord

logger = structlog.get_logger(__name__)

MAX_RETRIES = 3


class AnilistExtractor(BaseExtractor):
    """Extracts and normalizes manga data from AniList."""

    source_name = "anilist"
    MANGA_QUERY = """
    query ($ids: [Int], $perPage: Int) {
        Page(page: 1, perPage: $perPage) {
            media(type: MANGA, id_in: $ids) {
                id
                idMal
                title { romaji }
                description(asHtml: false)
                startDate { year month day }
                genres
                status
                averageScore
                staff(perPage: 25) {
                    edges {
                        role
                        node { name { full } }
                    }
                }
                stats { scoreDistribution { score amount } }
            }
        }
    }
    """
    MAX_ID_QUERY = """
    query {
        Page(page: 1, perPage: 1) {
            media(type: MANGA, sort: ID_DESC) { id }
        }
    }
    """
    STATUS_MAP = {
        "FINISHED": MangaStatus.FINISHED,
        "RELEASING": MangaStatus.ONGOING,
        "NOT_YET_RELEASED": MangaStatus.NOT_RELEASED_YET,
        "CANCELLED": MangaStatus.CANCELLED,
        "HIATUS": MangaStatus.HIATUS,
    }

    def __init__(self):
        """Load AniList settings for this extractor instance."""
        self.anilist_settings = get_anilist_settings()

    def _parse_response(self, response: httpx.Response) -> dict:
        """Raise for HTTP or GraphQL errors and return the parsed response body."""
        response.raise_for_status()
        body = response.json()
        if body.get("errors"):
            raise RuntimeError(f"AniList query failed: {body['errors']}")
        return body

    def _get_max_id(self) -> int:
        """Return the maximum manga ID available from AniList."""
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self.anilist_settings.base_url,
                json={"query": self.MAX_ID_QUERY},
            )
            return self._parse_response(response)["data"]["Page"]["media"][0]["id"]

    def _id_chunks(
        self,
        start_id: int,
        end_id: int,
        chunk_size: int,
    ) -> Iterator[list[int]]:
        """Yield chunks of manga IDs from start_id to end_id."""
        for i in range(start_id, end_id + 1, chunk_size):
            yield list(range(i, min(i + chunk_size, end_id + 1)))

    def _extract_author(self, media: dict) -> str:
        """Return a comma-separated list of story and art staff names."""
        staff_edges = media.get("staff", {}).get("edges", [])
        authors = [
            edge["node"]["name"]["full"]
            for edge in staff_edges
            if edge["role"].lower().startswith(("story", "art"))
        ]
        return ", ".join(authors) if authors else "Unknown"

    def _extract_status(self, media: dict) -> MangaStatus | None:
        """Map an AniList status string to a MangaStatus, or None if unmapped."""
        return self.STATUS_MAP.get(media.get("status", ""))

    def _extract_votes_count(self, media: dict) -> int | None:
        """Return the total vote count from AniList's score distribution."""
        score_distribution = media.get("stats", {}).get("scoreDistribution", [])
        if not score_distribution:
            return None
        return sum(item["amount"] for item in score_distribution)

    def _extract_description(self, media: dict) -> str | None:
        """Return the manga description with HTML tags stripped."""
        description = media.get("description")
        if description is None:
            return None
        return re.sub(r"<[^>]+>", "", description)

    def _extract_published_date(self, media: dict) -> datetime | None:
        """Return the manga's published date as a datetime object.

        Defaults a missing month or day to 1.
        """
        start_date = media.get("startDate") or {}
        year = start_date.get("year")
        month = start_date.get("month") or 1
        day = start_date.get("day", 1) or 1
        if year is None:
            return None
        return datetime(year, month, day, tzinfo=UTC)

    def _extract_score_distribution(self, media: dict) -> list[int] | None:
        """Return vote counts for AniList's 10 score buckets (10, 20, ..., 100).

        Bucket `i` holds the vote count for score `(i + 1) * 10`. Missing buckets
        are 0.
        """
        score_distribution = media.get("stats", {}).get("scoreDistribution", [])
        if not score_distribution:
            return None
        amounts_by_score = {
            item["score"]: item["amount"] for item in score_distribution
        }
        return [amounts_by_score.get((i + 1) * 10, 0) for i in range(10)]

    def _to_record(self, media: dict) -> NormalizedMangaRecord:
        """Convert a raw AniList media object into a NormalizedMangaRecord."""
        return NormalizedMangaRecord(
            external_id=str(media["id"]),
            mal_id=media["idMal"],
            title=media["title"]["romaji"],
            author=self._extract_author(media),
            status=self._extract_status(media),
            published_date=self._extract_published_date(media),
            description=self._extract_description(media),
            genres=media["genres"],
            raw_score=media["averageScore"],
            raw_scale_max=100.0,
            votes_count=self._extract_votes_count(media),
            score_distribution=self._extract_score_distribution(media),
            fetched_at=datetime.now(UTC),
        )

    async def _fetch_chunk(
        self,
        client: httpx.AsyncClient,
        limiter: AsyncLimiter,
        ids: list[int],
        attempt: int = 1,
    ) -> list[dict]:
        """Fetch one chunk of manga data from AniList.

        Waits for a free slot on the shared rate limiter before sending
        the request.
        """
        async with limiter:
            try:
                response = await client.post(
                    self.anilist_settings.base_url,
                    json={
                        "query": self.MANGA_QUERY,
                        "variables": {"ids": ids, "perPage": len(ids)},
                    },
                )
            except httpx.TransportError:
                if attempt >= MAX_RETRIES:
                    raise
                logger.warning("transport_error_retrying", attempt=attempt, ids=ids)
                await asyncio.sleep(2**attempt)
                return await self._fetch_chunk(client, limiter, ids, attempt + 1)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            logger.warning("rate_limited", retry_after=retry_after)
            await asyncio.sleep(retry_after)
            return await self._fetch_chunk(client, limiter, ids)

        return self._parse_response(response)["data"]["Page"]["media"]

    async def _stream(self) -> AsyncIterator[NormalizedMangaRecord]:
        """Yield normalized manga records asynchronously, as they arrive.

        Fetches all manga IDs concurrently, in fixed-size chunks, under a shared
        rate limit. This avoids AniList's page-based pagination, which caps out
        at 5,000 results.
        """
        rpm = self.anilist_settings.requests_per_minute
        min_id = self.anilist_settings.min_id
        chunk_size = self.anilist_settings.chunk_size
        max_id = self.anilist_settings.max_id or self._get_max_id()
        logger.info("max_id_resolved", max_id=max_id)

        limiter = AsyncLimiter(1, 60 / rpm)
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [
                self._fetch_chunk(client, limiter, ids)
                for ids in self._id_chunks(min_id, max_id, chunk_size)
            ]
            for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
                for media in await coro:
                    try:
                        record = self._to_record(media)
                    except Exception:
                        logger.warning(
                            "record_conversion_failed",
                            media_id=media.get("id"),
                            exc_info=True,
                        )
                        continue
                    yield record
                logger.info("chunk_fetched", chunk_number=i, total_chunks=len(tasks))
