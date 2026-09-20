"""Map a candidate source name to the source that runs it."""

from manga_recommender.recommender.base import BaseCandidateSource, Filter
from manga_recommender.recommender.candidate_sources.content import (
    ContentCandidateSource,
)
from manga_recommender.recommender.filters.dislikes import drop_near_dislikes
from manga_recommender.recommender.filters.exclusions import (
    exclude_manga_ids,
    exclude_manga_with_tags,
)

_SOURCE_MAP: dict[str, BaseCandidateSource] = {
    "content": ContentCandidateSource(),
}

_FILTERS: list[Filter] = [
    exclude_manga_ids,
    exclude_manga_with_tags,
    drop_near_dislikes,
]


def get_candidate_source(name: str) -> BaseCandidateSource:
    """Return the candidate source with the given name."""
    source = _SOURCE_MAP.get(name)
    if source is None:
        raise ValueError(f"Unknown candidate source: {name}")
    return source


def get_filters() -> list[Filter]:
    """Return every filter, in the order they must run."""
    return list(_FILTERS)
