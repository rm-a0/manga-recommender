"""Map a source name to its extractor class and default seed weight."""

from typing import NamedTuple

from manga_recommender.ingestion.base import BaseExtractor
from manga_recommender.ingestion.extractors.anilist import AnilistExtractor
from manga_recommender.ingestion.extractors.kaggle_mal import KaggleMalExtractor


class SourceRegistration(NamedTuple):
    """Represents a registered source and its associated extractor class."""

    extractor_class: type[BaseExtractor]
    weight: float = 1.0


_SOURCE_EXTRACTOR_MAP: dict[str, SourceRegistration] = {
    "anilist": SourceRegistration(
        weight=1.0,
        extractor_class=AnilistExtractor,
    ),
    "kaggle_mal": SourceRegistration(
        weight=0.5,
        extractor_class=KaggleMalExtractor,
    ),
}


def get_all_registered_sources() -> list[str]:
    """Return a list of all registered source names."""
    return list(_SOURCE_EXTRACTOR_MAP.keys())


def get_extractor_for_source(source_name: str) -> BaseExtractor:
    """Return an instance of the extractor class for the given source name."""
    registration = _SOURCE_EXTRACTOR_MAP.get(source_name)
    if registration is None:
        raise ValueError(f"Unknown source: {source_name}")
    return registration.extractor_class()


def get_source_weight(source_name: str) -> float:
    """Return the weight of the given source."""
    registration = _SOURCE_EXTRACTOR_MAP.get(source_name)
    if registration is None:
        raise ValueError(f"Unknown source: {source_name}")
    return registration.weight
