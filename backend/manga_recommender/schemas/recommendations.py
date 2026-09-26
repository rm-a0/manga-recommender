"""Request and response models for the recommendation routes."""

import uuid
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from manga_recommender.recommender.base import (
    DEFAULT_CANDIDATES_PER_SOURCE,
    DEFAULT_DISLIKE_SIMILARITY_CUTOFF,
    DEFAULT_LIMIT,
    DEFAULT_RANK_CONSTANT,
)
from manga_recommender.recommender.registry import get_source_names
from manga_recommender.schemas.manga import MangaSummary


class StrategyInfo(BaseModel):
    """One strategy and the weights it stands for.

    A client reads this to show the weights of a strategy before it sends a
    request.
    """

    strategy: str
    weights: dict[str, float]


class RecommendationStrategy(StrEnum):
    """A named blend of the candidate sources.

    Each strategy holds one weight per source. A request can override single
    weights without naming the rest.
    """

    AUTO = "auto"
    BALANCED = "balanced"
    CONTENT = "content"
    TAGS = "tags"


class RecommendationRequest(BaseModel):
    """What the reader asks for in one recommendation request.

    `weights` overrides single weights of the chosen strategy. The strategy
    supplies every weight the request leaves out.
    """

    liked_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    disliked_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)
    exclude_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    exclude_tags: list[str] = Field(default_factory=list, max_length=200)
    strategy: RecommendationStrategy = RecommendationStrategy.AUTO
    weights: dict[str, Annotated[float, Field(ge=0)]] | None = None
    dislike_similarity_cutoff: float = Field(
        DEFAULT_DISLIKE_SIMILARITY_CUTOFF, ge=0, le=1
    )
    rank_constant: int = Field(DEFAULT_RANK_CONSTANT, ge=1, le=100)
    candidates_per_source: int = Field(DEFAULT_CANDIDATES_PER_SOURCE, ge=1, le=1000)
    limit: int = Field(DEFAULT_LIMIT, ge=1, le=50)

    @field_validator("weights")
    @classmethod
    def _reject_unknown_sources(cls, value):
        """Reject a weight that names no candidate source."""
        if value is None:
            return value
        unknown = value.keys() - get_source_names()
        if unknown:
            raise ValueError(f"Unknown candidate sources: {sorted(unknown)}")
        return value


class RecommendationSeed(BaseModel):
    """A liked manga that the run started from.

    Holds the title, so a client that has only ids can name the seed of a
    reason.
    """

    id: uuid.UUID
    title: str


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
