"""Build recommendation queries for the recommender tests."""

from dataclasses import replace

from manga_recommender.recommender.base import (
    DEFAULT_CANDIDATES_PER_SOURCE,
    DEFAULT_DISLIKE_SIMILARITY_CUTOFF,
    DEFAULT_LIMIT,
    DEFAULT_RANK_CONSTANT,
    RecommendationQuery,
)

_BASE_QUERY = RecommendationQuery(
    liked_ids=(),
    disliked_ids=(),
    source_weights={"content": 1.0},
    exclude_ids=frozenset(),
    excluded_tags=frozenset(),
    dislike_similarity_cutoff=DEFAULT_DISLIKE_SIMILARITY_CUTOFF,
    rank_constant=DEFAULT_RANK_CONSTANT,
    candidates_per_source=DEFAULT_CANDIDATES_PER_SOURCE,
    limit=DEFAULT_LIMIT,
)


def make_query(**overrides: object) -> RecommendationQuery:
    """Return a query with the engine defaults, and the given fields replaced."""
    return replace(_BASE_QUERY, **overrides)  # type: ignore[arg-type]
