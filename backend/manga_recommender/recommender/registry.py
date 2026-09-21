"""Hold the candidate sources, filters, scorers and selectors that a run uses.

List order is run order.
"""

from manga_recommender.recommender.base import (
    BaseCandidateSource,
    Filter,
    Scorer,
    Selector,
)
from manga_recommender.recommender.candidate_sources.content import (
    ContentCandidateSource,
)
from manga_recommender.recommender.candidate_sources.tags import TagsCandidateSource
from manga_recommender.recommender.filters.dislikes import drop_near_dislikes
from manga_recommender.recommender.filters.exclusions import (
    exclude_manga_ids,
    exclude_manga_with_tags,
)
from manga_recommender.recommender.scorers.rank_fusion import weighted_rank_fusion
from manga_recommender.recommender.selectors.top_k import take_top_k

_SOURCE_MAP: dict[str, BaseCandidateSource] = {
    "content": ContentCandidateSource(),
    "tags": TagsCandidateSource(),
}

_FILTERS: list[Filter] = [
    exclude_manga_ids,
    exclude_manga_with_tags,
    drop_near_dislikes,
]

_SCORERS: list[Scorer] = [
    weighted_rank_fusion,
]

_SELECTORS: list[Selector] = [
    take_top_k,
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


def get_scorers() -> list[Scorer]:
    """Return every scorer, in the order they must run."""
    return list(_SCORERS)


def get_selectors() -> list[Selector]:
    """Return every selector, in the order they must run."""
    return list(_SELECTORS)
