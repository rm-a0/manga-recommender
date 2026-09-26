"""Shared types for the recommender: the query, the candidates, and each stage's shape."""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Final

from sqlalchemy.orm import Session

# The defaults that the API applies. The query itself has none.
DEFAULT_RANK_CONSTANT: Final[int] = 60
DEFAULT_DISLIKE_SIMILARITY_CUTOFF: Final[float] = 0.9
# About four times the largest `limit`, because the filters drop candidates.
DEFAULT_CANDIDATES_PER_SOURCE: Final[int] = 200
DEFAULT_LIMIT: Final[int] = 20


@dataclass(frozen=True, slots=True, kw_only=True)
class RecommendationQuery:
    """Hold what the reader asked for. The service builds it from the request.

    `source_weights` names the candidate sources to run. A source that is not
    a key does not run. The values set how much each source's ranking counts
    when the scorer combines them. Only their ratios matter, so they need not
    sum to 1.

    `dislike_similarity_cutoff` is a cosine similarity. `candidates_per_source`
    sets how many candidates each source nominates, before the merge.

    No field has a default, so a caller that forgets one fails at once. The
    `DEFAULT_*` constants hold the values that the API uses.
    """

    liked_ids: tuple[uuid.UUID, ...]
    disliked_ids: tuple[uuid.UUID, ...]
    source_weights: Mapping[str, float]
    exclude_ids: frozenset[uuid.UUID]
    excluded_tags: frozenset[str]
    dislike_similarity_cutoff: float
    rank_constant: int
    candidates_per_source: int
    limit: int


@dataclass(frozen=True, slots=True)
class Reason:
    """Record why a candidate source nominated a candidate.

    Holds ids, not text. The service writes the text, because it already
    loads the manga titles.
    """

    source: str
    seed_id: uuid.UUID | None = None


@dataclass(slots=True)
class Candidate:
    """Hold one manga that a candidate source nominated.

    The runner fills `source_ranks` when it merges the sources, and the scorer
    fills `score`. A candidate source only sets `manga_id` and `reasons`.
    """

    manga_id: uuid.UUID
    reasons: list[Reason] = field(default_factory=list)
    source_ranks: dict[str, int] = field(default_factory=dict)
    score: float = 0.0


class BaseCandidateSource(ABC):
    """Interface for the sources that nominate candidates from the catalogue."""

    name: str

    @abstractmethod
    def get_candidates(
        self,
        db: Session,
        query: RecommendationQuery,
        k: int,
    ) -> list[Candidate]:
        """Return up to `k` candidates, best first."""


type Filter = Callable[[Session, RecommendationQuery, list[Candidate]], list[Candidate]]
"""Return the candidates that the query allows. Judge each candidate alone."""

type Scorer = Callable[[RecommendationQuery, list[Candidate]], list[Candidate]]
"""Return the same candidates, each with its `score` set.

The first scorer sets the score. A later scorer adjusts the score it reads,
so that each scorer keeps the work of the one before it.
"""

type Selector = Callable[[RecommendationQuery, list[Candidate]], list[Candidate]]
"""Return the final candidates, in display order. Judge the list as a whole.

A selector that cuts the list runs last. A selector after it reads only the
candidates that are left.
"""
