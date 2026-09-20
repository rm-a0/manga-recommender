"""Nominate manga that share tags with the manga the reader liked."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga import (
    get_manga_ids_by_tag_ids,
    get_tag_ids_by_manga_ids,
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


class TagsCandidateSource(BaseCandidateSource):
    """Nominate the manga that share the most tags with each liked manga.

    Answers for a manga that has no embedding, which the content source cannot
    reach.
    """

    name = "tags"

    def _find_matches(
        self,
        db: Session,
        seed_ids: Sequence[uuid.UUID],
        k: int,
    ) -> list[SeedMatches]:
        """Return the `k` manga that share the most tags with each seed.

        Skip a seed that carries no tag. Each seed keeps its own tags, so two
        seeds of different taste each get their own matches.
        """
        matches: list[SeedMatches] = []

        for seed_id, tag_ids in get_tag_ids_by_manga_ids(db, seed_ids):
            match_ids = [id_ for id_, _ in get_manga_ids_by_tag_ids(db, tag_ids, k)]
            matches.append(SeedMatches(seed_id=seed_id, match_ids=match_ids))

        return matches

    def get_candidates(
        self,
        db: Session,
        query: RecommendationQuery,
        k: int,
    ) -> list[Candidate]:
        """Return up to `k` candidates, best first."""
        matches_per_seed = self._find_matches(db, query.liked_ids, k)
        return round_robin_merge(matches_per_seed, query.liked_ids, self.name, k)
