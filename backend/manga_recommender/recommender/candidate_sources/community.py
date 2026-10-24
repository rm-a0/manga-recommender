"""Nominate manga that readers recommend for the manga the reader liked."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_similarities import SimilarityMethod
from manga_recommender.db.repositories.manga import MangaFilters
from manga_recommender.db.repositories.manga_similarities import get_similar_manga_ids
from manga_recommender.recommender.base import (
    BaseCandidateSource,
    Candidate,
    RecommendationQuery,
)
from manga_recommender.recommender.candidate_sources.common import (
    SeedMatches,
    round_robin_merge,
)


class CommunityCandidateSource(BaseCandidateSource):
    """Nominate the manga that AniList readers recommend for each liked manga.

    Reads the `community_recs` edges in `manga_similarities`. A liked manga
    that no reader wrote a recommendation for gets no matches.
    """

    name = "community"

    def _find_matches(
        self,
        db: Session,
        seed_ids: Sequence[uuid.UUID],
        filters: MangaFilters,
        k: int,
    ) -> list[SeedMatches]:
        """Return the `k` best-scored recommendations for each seed.

        Match only the manga that pass `filters`. Each seed keeps its own
        list, so two seeds of different taste each get their own matches.
        """
        return [
            SeedMatches(
                seed_id=seed_id,
                match_ids=get_similar_manga_ids(
                    db, seed_id, SimilarityMethod.COMMUNITY_RECS, filters, k
                ),
            )
            for seed_id in seed_ids
        ]

    def get_candidates(
        self,
        db: Session,
        query: RecommendationQuery,
        k: int,
    ) -> list[Candidate]:
        """Return up to `k` candidates, best first."""
        matches_per_seed = self._find_matches(db, query.liked_ids, query.filters, k)
        return round_robin_merge(matches_per_seed, query.liked_ids, self.name, k)
