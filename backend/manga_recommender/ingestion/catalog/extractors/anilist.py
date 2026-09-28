"""Extractor that pulls manga data from the AniList GraphQL API."""

import asyncio
import html
import re
from calendar import monthrange
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import structlog

from manga_recommender.core.config import get_anilist_settings
from manga_recommender.db.models.manga import MangaStatus, MangaType
from manga_recommender.ingestion.anilist.client import AnilistClient
from manga_recommender.ingestion.anilist.paging import (
    get_max_manga_id,
    id_chunks,
)
from manga_recommender.ingestion.catalog.base import (
    BaseExtractor,
    NormalizedMangaRecord,
    NormalizedTag,
)

logger = structlog.get_logger(__name__)


class AnilistExtractor(BaseExtractor):
    """Extracts and normalizes manga data from AniList."""

    source_name = "anilist"
    MANGA_QUERY = """
    query ($ids: [Int], $perPage: Int) {
        Page(page: 1, perPage: $perPage) {
            media(type: MANGA, id_in: $ids) {
                id
                idMal
                format
                countryOfOrigin
                title { romaji english }
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
                tags { 
                    name
                    rank
                    category
                    isMediaSpoiler
                    isGeneralSpoiler
                    isAdult
                }
                coverImage { large }
                isAdult
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
    BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
    HTML_TAG_RE = re.compile(r"<[^>]+>")
    DESCRIPTION_NOISE = (
        re.compile(r"~!|!~"),
        re.compile(r"\(Source[^)]*\)"),
    )
    FORMAT_MAP = {
        "NOVEL": MangaType.LIGHT_NOVEL,
        "ONE_SHOT": MangaType.ONE_SHOT,
    }
    ORIGIN_MAP = {
        "KR": MangaType.MANHWA,
        "CN": MangaType.MANHUA,
    }

    def __init__(self):
        """Load AniList settings for this extractor instance."""
        self.anilist_settings = get_anilist_settings()

    def _extract_authors(self, media: dict) -> list[str]:
        """Return the names of the story and art staff, without repeats.

        One person credited for both story and art appears once.
        """
        staff_edges = media.get("staff", {}).get("edges", [])
        names = [
            edge["node"]["name"]["full"]
            for edge in staff_edges
            if edge["role"].lower().startswith(("story", "art"))
        ]
        return list(dict.fromkeys(names))

    def _extract_status(self, media: dict) -> MangaStatus | None:
        """Map an AniList status string to a MangaStatus, or None if unmapped."""
        return self.STATUS_MAP.get(media.get("status", ""))

    def _extract_votes_count(self, media: dict) -> int | None:
        """Return the total vote count from AniList's score distribution."""
        score_distribution = media.get("stats", {}).get("scoreDistribution", [])
        if not score_distribution:
            return None
        return sum(item["amount"] for item in score_distribution)

    def _clean_description(self, raw: str) -> str:
        """Return the description without markup, spoiler marks or attribution.

        A <br> becomes a line break, so the words around it stay apart. The
        unescape runs after the strip, so an escaped bracket stays text.
        """
        text = self.BREAK_RE.sub("\n", raw)
        text = html.unescape(self.HTML_TAG_RE.sub("", text))
        for pattern in self.DESCRIPTION_NOISE:
            text = pattern.sub("", text)
        return text

    def _extract_description(self, media: dict) -> str | None:
        """Return the manga description, cleaned, or None if absent."""
        raw = media.get("description")
        return self._clean_description(raw) if raw else None

    def _extract_published_date(self, media: dict) -> datetime | None:
        """Return the manga's published date as a datetime object.

        Defaults a missing month or day to 1. AniList returns days that the
        month does not have. The day is clamped, because raising here would
        drop the whole record.
        """
        start_date = media.get("startDate") or {}
        year = start_date.get("year")
        if year is None:
            return None
        month = min(max(start_date.get("month") or 1, 1), 12)
        day = max(start_date.get("day") or 1, 1)
        return datetime(year, month, min(day, monthrange(year, month)[1]), tzinfo=UTC)

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

    def _extract_tags(self, media: dict) -> list[NormalizedTag] | None:
        """Return the media's tags and genres as one list, or None if it has neither.

        Tags come first, so a genre that normalizes onto a tag keeps AniList's
        own category instead of `Genre`. AniList does not send `Genre`.
        """
        tags = media["tags"]
        genres = media["genres"]
        if not tags and not genres:
            return None
        return [
            *(
                NormalizedTag(
                    name=tag["name"],
                    category=tag["category"],
                    rank=tag["rank"],
                    is_spoiler=tag["isGeneralSpoiler"] or tag["isMediaSpoiler"],
                    is_explicit=tag["isAdult"],
                )
                for tag in tags
            ),
            *(
                NormalizedTag(
                    name=genre,
                    category="Genre",
                    rank=None,
                    is_spoiler=False,
                    is_explicit=False,
                )
                for genre in genres
            ),
        ]

    def _extract_image_url(self, media: dict) -> str | None:
        """Return the large cover image URL, or None if the media has no cover."""
        image_url = (media.get("coverImage") or {}).get("large")
        if not image_url:
            return None
        return image_url

    def _extract_type(self, media: dict) -> MangaType | None:
        """Return the medium of the media object.

        AniList splits the medium over two fields. `format` gives the shape, and
        `countryOfOrigin` separates a manhwa or a manhua from a manga. The query
        asks for manga, so an unlisted format still gives `MANGA`. AniList has no
        doujinshi format, and its `NOVEL` covers light novels as well.
        """
        format_ = media["format"]
        origin = media["countryOfOrigin"]
        if format_ in self.FORMAT_MAP:
            return self.FORMAT_MAP.get(format_)
        elif origin in self.ORIGIN_MAP:
            return self.ORIGIN_MAP.get(origin)
        return MangaType.MANGA

    def _to_record(self, media: dict) -> NormalizedMangaRecord:
        """Convert a raw AniList media object into a NormalizedMangaRecord."""
        return NormalizedMangaRecord(
            external_id=str(media["id"]),
            mal_id=media["idMal"],
            title=media["title"]["romaji"],
            title_english=media["title"]["english"],
            type=self._extract_type(media),
            authors=self._extract_authors(media),
            status=self._extract_status(media),
            published_date=self._extract_published_date(media),
            description=self._extract_description(media),
            tags=self._extract_tags(media),
            raw_score=media["averageScore"],
            raw_scale_max=100.0,
            votes_count=self._extract_votes_count(media),
            score_distribution=self._extract_score_distribution(media),
            fetched_at=datetime.now(UTC),
            image_url=self._extract_image_url(media),
            is_explicit=media["isAdult"],
        )

    async def _fetch_chunk_records(
        self,
        client: AnilistClient,
        ids: list[int],
    ) -> list[NormalizedMangaRecord] | None:
        """Fetch one chunk and convert it to records.

        Return None if the chunk fails after retries. Skip any media object
        that fails to convert.
        """
        try:
            data = await client.execute(
                self.MANGA_QUERY, {"ids": ids, "perPage": len(ids)}
            )
            media_list = data["Page"]["media"]
        except Exception:
            logger.warning(
                "chunk_failed", first_id=ids[0], last_id=ids[-1], exc_info=True
            )
            return None
        records = []
        for media in media_list:
            try:
                records.append(self._to_record(media))
            except Exception:
                logger.warning(
                    "record_conversion_failed", media_id=media.get("id"), exc_info=True
                )
        return records

    async def _stream(self) -> AsyncIterator[NormalizedMangaRecord]:
        """Yield normalized manga records asynchronously, as they arrive.

        Fetches all manga IDs concurrently, in fixed-size chunks, under a shared
        rate limit. This avoids AniList's page-based pagination, which caps out
        at 5,000 results.
        """
        settings = self.anilist_settings
        async with AnilistClient(
            rpm=settings.requests_per_minute,
            base_url=settings.base_url,
        ) as client:
            max_id = settings.max_id or await get_max_manga_id(client)
            logger.info("max_id_resolved", max_id=max_id)
            tasks = [
                self._fetch_chunk_records(client, ids)
                for ids in id_chunks(
                    settings.min_id, max_id, settings.catalog_chunk_size
                )
            ]
            failed = 0
            for i, coro in enumerate(asyncio.as_completed(tasks), start=1):
                records = await coro
                if records is None:
                    failed += 1
                    continue
                for record in records:
                    yield record
                logger.info("chunk_fetched", chunk_number=i, total_chunks=len(tasks))

            if failed:
                logger.warning("chunks_failed", failed=failed, total=len(tasks))
