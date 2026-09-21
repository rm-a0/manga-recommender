"""Select the highest scored candidates, in display order."""

from operator import attrgetter

from manga_recommender.recommender.base import Candidate, RecommendationQuery


def take_top_k(
    query: RecommendationQuery,
    candidates: list[Candidate],
) -> list[Candidate]:
    """Return the `query.limit` highest scored candidates, best first.

    The sort is stable, so two candidates of equal score keep the order the
    candidate sources gave them. This selector cuts the list, so it must run
    last.
    """
    return sorted(candidates, key=attrgetter("score"), reverse=True)[: query.limit]
