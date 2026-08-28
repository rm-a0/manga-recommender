"""Extractor that pulls manga data from the Kaggle MAL dataset."""

import csv
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import structlog

from manga_recommender.config import get_kaggle_mal_settings
from manga_recommender.db.models.manga import MangaStatus
from manga_recommender.ingestion.base import BaseExtractor, NormalizedMangaRecord

logger = structlog.get_logger(__name__)


class KaggleMalExtractor(BaseExtractor):
    """Extracts and normalizes manga data from Kaggle MAL dataset."""

    source_name = "kaggle_mal"
    STATUS_MAP = {
        "Finished": MangaStatus.FINISHED,
        "Publishing": MangaStatus.ONGOING,
        "On Hiatus": MangaStatus.HIATUS,
        "Discontinued": MangaStatus.CANCELLED,
    }

    def __init__(self):
        """Initialize the Kaggle MAL extractor."""
        self.kaggle_mal_settings = get_kaggle_mal_settings()

    def _extract_status(self, row: dict[str, str]) -> MangaStatus | None:
        """Map the row's status string to a MangaStatus, or None if unmapped."""
        return self.STATUS_MAP.get(row.get("status", ""))

    def _extract_published_date(self, row: dict[str, str]) -> datetime | None:
        """Return the publication start date as a UTC datetime, or None if absent.

        The dataset's `published_from` is always `YYYY-MM-DD` when present.
        """
        date_raw = row.get("published_from")
        if not date_raw:
            return None
        return datetime.strptime(date_raw, "%Y-%m-%d").replace(tzinfo=UTC)

    def _split_pipe(self, value: str) -> list[str]:
        """Split a pipe-delimited field into stripped, non-empty parts."""
        return [part.strip() for part in value.split("|") if part.strip()]

    def _extract_authors(self, row: dict[str, str]) -> list[str]:
        """Return the row's author names, without repeats."""
        return list(dict.fromkeys(self._split_pipe(row.get("authors", ""))))

    def _extract_genres(self, row: dict[str, str]) -> list[str] | None:
        """Return the row's genres, themes, and demographics as one tag list."""
        genres = self._split_pipe(row.get("genres", ""))
        genres.extend(self._split_pipe(row.get("themes", "")))
        genres.extend(self._split_pipe(row.get("demographics", "")))
        return genres

    def _extract_int(self, value: str) -> int | None:
        """Parse an integer, returning None for an empty string."""
        return int(value) if value else None

    def _extract_float(self, value: str) -> float | None:
        """Parse a float, returning None for an empty string."""
        return float(value) if value else None

    def _to_record(self, row: dict[str, str]) -> NormalizedMangaRecord:
        """Convert one CSV row into a NormalizedMangaRecord.

        Raise if the row has no mal_id or no title. Both default to an empty
        string otherwise, which would collapse every such row onto one manga.
        """
        mal_id = self._extract_int(row.get("mal_id", ""))
        if mal_id is None:
            raise ValueError("row has no mal_id")
        title = row.get("title", "").strip()
        if not title:
            raise ValueError(f"row {mal_id} has no title")
        return NormalizedMangaRecord(
            external_id=str(mal_id),
            mal_id=mal_id,
            title=title,
            authors=self._extract_authors(row),
            status=self._extract_status(row),
            published_date=self._extract_published_date(row),
            description=row.get("synopsis") or None,
            genres=self._extract_genres(row),
            raw_score=self._extract_float(row.get("score", "")),
            raw_scale_max=10.0,
            votes_count=self._extract_int(row.get("scored_by", "")),
            score_distribution=None,
            fetched_at=datetime.now(UTC),
        )

    async def _stream(self) -> AsyncIterator[NormalizedMangaRecord]:
        """Yield one normalized record per row of the local Kaggle MAL CSV.

        Log and skip any row that fails to convert, so one bad row does not
        stop the run.
        """
        filename = self.kaggle_mal_settings.path
        with open(filename, newline="", encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                try:
                    record = self._to_record(row)
                except Exception:
                    logger.warning(
                        "record_conversion_failed",
                        media_id=row.get("mal_id"),
                        exc_info=True,
                    )
                    continue
                yield record
