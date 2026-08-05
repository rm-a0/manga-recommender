from abc import ABC, abstractmethod
from collections.abc import Iterator

from pydantic.dataclasses import dataclass

from manga_recommender.db.models.manga import MangaStatus


@dataclass
class NormalizedMangaRecord:
    external_id: str
    mal_id: int | None
    title: str
    author: str
    status: MangaStatus | None
    description: str | None
    genres: list[str] | None
    raw_score: float | None
    raw_scale_max: float | None
    votes_count: int | None


class BaseExtractor(ABC):
    source_name: str

    @abstractmethod
    def extract(self) -> Iterator[NormalizedMangaRecord]:
        pass
