"""Request and response models for the recommendation routes."""

import uuid
from enum import StrEnum

from pydantic import BaseModel

from manga_recommender.schemas.manga import MangaSummary


class RecommendationStrategy(StrEnum):
    """A named blend of the candidate sources.

    Each strategy holds one weight per source. A request can override single
    weights without naming the rest.
    """

    CONTENT = "content"
    TAGS = "tags"
    BALANCED = "balanced"


class RecommendationRequest(BaseModel):
    """What the reader asks for in one recommendation request.

    `weights` overrides single weights of the chosen strategy. The strategy
    supplies every weight the request leaves out.
    """

    liked_ids: list[uuid.UUID]
    disliked_ids: list[uuid.UUID] = []
    exclude_ids: list[uuid.UUID] = []
    exclude_tags: list[str] = []
    strategy: RecommendationStrategy = RecommendationStrategy.BALANCED
    weights: dict[str, float] | None = None
    limit: int = 20


class RecommendationSeed(BaseModel):
    """A liked manga that the run started from.

    `used_sources` names the sources that could use the seed. A source that
    needs an embedding skips a manga that has none.
    """

    id: uuid.UUID
    title: str
    used_sources: list[str]


class RecommendationReason(BaseModel):
    """Why one candidate source nominated a manga.

    Names the seed by id. The seed itself sits once in `RecommendationResult`.
    """

    source: str
    seed_id: uuid.UUID | None


class Recommendation(BaseModel):
    """One recommended manga, with the reasons that nominated it."""

    manga: MangaSummary
    reasons: list[RecommendationReason]


class RecommendationResult(BaseModel):
    """The recommendations of one run, in display order.

    Holds no page window, because a run returns its whole result. A larger
    `limit` is the only way to ask for more.
    """

    recommendations: list[Recommendation]
    strategy: RecommendationStrategy
    seeds: list[RecommendationSeed]
