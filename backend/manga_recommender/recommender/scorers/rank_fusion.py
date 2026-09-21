"""Score a candidate by its rank in each source that nominated it."""

from collections.abc import Mapping
from typing import Final

from manga_recommender.recommender.base import Candidate, RecommendationQuery

_RANK_CONSTANT: Final[int] = 60


def _score(source_weights: Mapping[str, float], source_ranks: dict[str, int]) -> float:
    """Return the reciprocal rank fusion score of one candidate.

    Each source adds its weight divided by the rank it gave the candidate. The
    rank constant keeps the first ranks from dwarfing the rest, so a candidate
    that several sources rank well beats one that a single source ranks first.
    """
    score = 0.0
    for source_name, candidate_rank in source_ranks.items():
        score += source_weights[source_name] * (1 / (_RANK_CONSTANT + candidate_rank))
    return score


def weighted_rank_fusion(
    query: RecommendationQuery,
    candidates: list[Candidate],
) -> list[Candidate]:
    """Set the score of every candidate, and return the same list.

    Reads the weight of each source from the query. A source that nominated no
    candidate changes nothing.
    """
    for candidate in candidates:
        candidate.score = _score(query.source_weights, candidate.source_ranks)
    return candidates
