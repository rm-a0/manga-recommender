"""Business logic for the recommendation routes."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.repositories.manga import get_manga_by_ids
from manga_recommender.recommender.base import Candidate, Reason, RecommendationQuery
from manga_recommender.recommender.runner import run_recommender
from manga_recommender.schemas.recommendations import (
    Recommendation,
    RecommendationReason,
    RecommendationRequest,
    RecommendationResult,
    RecommendationSeed,
    RecommendationStrategy,
    StrategyInfo,
)
from manga_recommender.services.manga import to_manga_summary

_STRATEGY_WEIGHTS: dict[RecommendationStrategy, dict[str, float]] = {
    RecommendationStrategy.AUTO: {"content": 1.0, "tags": 0.5},
    RecommendationStrategy.BALANCED: {"content": 1.0, "tags": 1.0},
    RecommendationStrategy.CONTENT: {"content": 1.0},
    RecommendationStrategy.TAGS: {"tags": 1.0},
}


def get_strategy_info() -> list[StrategyInfo]:
    """Return every strategy and the weights it stands for."""
    return [
        StrategyInfo(strategy=strategy, weights=weights)
        for strategy, weights in _STRATEGY_WEIGHTS.items()
    ]


def _to_query(request: RecommendationRequest) -> RecommendationQuery:
    """Map request vocabulary to recommender vocabulary.

    The request weights override single weights of the strategy. The strategy
    supplies every weight the request leaves out.
    """
    return RecommendationQuery(
        liked_ids=tuple(request.liked_ids),
        disliked_ids=tuple(request.disliked_ids),
        source_weights={
            **_STRATEGY_WEIGHTS[request.strategy],
            **(request.weights or {}),
        },
        exclude_ids=frozenset(request.exclude_ids),
        excluded_tags=frozenset(request.exclude_tags),
        dislike_similarity_cutoff=request.dislike_similarity_cutoff,
        rank_constant=request.rank_constant,
        candidates_per_source=request.candidates_per_source,
        limit=request.limit,
    )


def _to_reasons(reasons: Sequence[Reason]) -> list[RecommendationReason]:
    """Map the reasons of one candidate to their response models."""
    return [RecommendationReason(source=r.source, seed_id=r.seed_id) for r in reasons]


def _to_recommendations(
    candidates: Sequence[Candidate],
    manga_by_id: dict[uuid.UUID, Manga],
) -> list[Recommendation]:
    """Map the candidates to their response models, in the order given.

    `manga_by_id` must hold a row for every candidate.
    """
    return [
        Recommendation(
            manga=to_manga_summary(manga_by_id[candidate.manga_id]),
            reasons=_to_reasons(candidate.reasons),
        )
        for candidate in candidates
    ]


def get_recommendations(
    db: Session,
    request: RecommendationRequest,
) -> RecommendationResult:
    """Return the recommendations for one request.

    Reads the candidate manga and the seed manga in two separate queries,
    because a seed is never a candidate.
    """
    query = _to_query(request)
    candidates = run_recommender(db, query)
    manga_by_id = {
        m.id: m for m in get_manga_by_ids(db, [c.manga_id for c in candidates])
    }
    return RecommendationResult(
        recommendations=_to_recommendations(candidates, manga_by_id),
        strategy=request.strategy,
        seeds=[
            RecommendationSeed(id=m.id, title=m.title)
            for m in get_manga_by_ids(db, query.liked_ids)
        ],
    )
