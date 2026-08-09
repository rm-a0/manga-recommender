"""Extractor that pulls manga data from the AniList GraphQL API."""

import re
import time
from collections.abc import Iterator

import httpx

from manga_recommender.config import get_anilist_settings
from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.ingestion.base import BaseExtractor, NormalizedMangaRecord


class AnilistExtractor(BaseExtractor):
    """Extracts and normalizes manga data from AniList."""

    source_name = "anilist"
    query = """
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            pageInfo { hasNextPage }
            media(type: MANGA, sort: ID) {
                id
                idMal
                title { romaji }
                description(asHtml: false)
                genres
                status
                averageScore
                staff(perPage: 25) {
                    edges {
                        role
                        node { name { full } }
                    }
                }
                stats { scoreDistribution { amount } }
            }
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
        self.anilist_settings = get_anilist_settings()

    def _should_continue(self, page: int) -> bool:
        """Return whether the given page is within the configured page limit."""
        return (
            self.anilist_settings.max_pages is None
            or page <= self.anilist_settings.max_pages
        )

    def _fetch_page(self, client: httpx.Client, page: int) -> dict:
        """Fetch one page of manga from the AniList API.

        Retries automatically after the server's Retry-After delay on a 429 response.
        """
        response = client.post(
            self.anilist_settings.base_url,
            json={
                "query": self.query,
                "variables": {"page": page, "perPage": self.anilist_settings.per_page},
            },
        )
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            time.sleep(retry_after)
            return self._fetch_page(client, page)

        response.raise_for_status()

        body = response.json()

        if body.get("errors"):
            raise RuntimeError(f"AniList query failed: {body['errors']}")
        return body

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

    def _to_record(self, media: dict) -> NormalizedMangaRecord:
        """Convert a raw AniList media object into a NormalizedMangaRecord."""
        return NormalizedMangaRecord(
            external_id=str(media["id"]),
            mal_id=media["idMal"],
            title=media["title"]["romaji"],
            author=self._extract_author(media),
            status=self._extract_status(media),
            published_date=None,  # TODO: Extract published date if available
            description=self._extract_description(media),
            genres=media["genres"],
            raw_score=media["averageScore"],
            raw_scale_max=100.0,
            votes_count=self._extract_votes_count(media),
        )

    def extract(self) -> Iterator[NormalizedMangaRecord]:
        """Yield normalized manga records for every page of AniList manga data."""
        with httpx.Client(timeout=30.0) as client:
            page = 1
            while self._should_continue(page):
                body = self._fetch_page(client, page)
                for media in body["data"]["Page"]["media"]:
                    yield self._to_record(media)
                if not body["data"]["Page"]["pageInfo"]["hasNextPage"]:
                    break
                page += 1
                time.sleep(self.anilist_settings.request_delay)
