"""Nominate manga whose content vectors are near the manga the reader liked."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga import MangaFilters
from manga_recommender.db.repositories.manga_embeddings import (
    get_embedding_by_manga_id,
    get_nearest_neighbours,
)
from manga_recommender.recommender.base import (
    BaseCandidateSource,
    Candidate,
    RecommendationQuery,
)
from manga_recommender.recommender.candidate_sources.common import (
    SeedMatches,
    round_robin_merge,
)


class ContentCandidateSource(BaseCandidateSource):
    """Nominate the nearest neighbours of each liked manga by content vector."""

    name = "content"

    def _find_matches(
        self,
        db: Session,
        seed_ids: Sequence[uuid.UUID],
        filters: MangaFilters,
        k: int,
    ) -> list[SeedMatches]:
        """Return the `k` nearest manga of each seed, among those that pass `filters`.

        Skip a seed that has no embedding.
        """
        matches: list[SeedMatches] = []
        for seed_id in seed_ids:
            embedding = get_embedding_by_manga_id(db, seed_id)
            if not embedding:
                continue

            match_ids = get_nearest_neighbours(db, embedding, filters, k)
            matches.append(SeedMatches(seed_id=seed_id, match_ids=match_ids))

        return matches

    def get_candidates(
        self,
        db: Session,
        query: RecommendationQuery,
        k: int,
    ) -> list[Candidate]:
        """Return up to `k` candidates, best first."""
        matches_per_seed = self._find_matches(db, query.liked_ids, query.filters, k)
        return round_robin_merge(matches_per_seed, query.liked_ids, self.name, k)
