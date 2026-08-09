"""Base extractor interface and the normalized manga record shape."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime

from pydantic.dataclasses import dataclass

from manga_recommender.db.models.manga import MangaStatus


@dataclass
class NormalizedMangaRecord:
    """Manga data in a source-independent shape, ready for loading."""

    external_id: str
    mal_id: int | None
    title: str
    author: str
    status: MangaStatus | None
    description: str | None
    genres: list[str] | None
    published_date: datetime | None
    raw_score: float | None
    raw_scale_max: float | None
    votes_count: int | None
    fetched_at: datetime


class BaseExtractor(ABC):
    """Interface for extractors that pull manga data from an external source."""

    source_name: str

    @abstractmethod
    def extract(self) -> Iterator[NormalizedMangaRecord]:
        """Yield normalized manga records from the source."""
        pass
