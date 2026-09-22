"""HTTP routes for the recommendation resource."""

from fastapi import APIRouter

from manga_recommender.api.dependencies import DbSession
from manga_recommender.schemas.recommendations import (
    RecommendationRequest,
    RecommendationResult,
    StrategyInfo,
)
from manga_recommender.services.recommendations import (
    get_recommendations,
    get_strategy_info,
)

router: APIRouter = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("", response_model=RecommendationResult)
def recommend_manga(
    db: DbSession,
    request: RecommendationRequest,
) -> RecommendationResult:
    """Return the recommendations for one request.

    Uses POST, because the query holds more than a URL can carry.
    """
    return get_recommendations(db, request)


@router.get("/strategies", response_model=list[StrategyInfo])
def list_strategies() -> list[StrategyInfo]:
    """Return every strategy and the weights it stands for.

    Reads no table, so a client can call it once and keep the answer.
    """
    return get_strategy_info()
