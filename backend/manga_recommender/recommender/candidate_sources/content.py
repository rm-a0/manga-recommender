"""Nominate manga whose content vectors are near the manga the reader liked."""

import uuid
from collections.abc import Collection, Sequence
from typing import NamedTuple

from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga_embeddings import (
    get_embedding_by_manga_id,
    get_nearest_neighbours,
)
from manga_recommender.recommender.base import (
    BaseCandidateSource,
    Candidate,
    Reason,
    RecommendationQuery,
)


class SeedMatches(NamedTuple):
    """Hold one liked manga and the ids of its nearest manga, nearest first."""

    seed_id: uuid.UUID
    match_ids: Sequence[uuid.UUID]


class ContentCandidateSource(BaseCandidateSource):
    """Nominate the nearest neighbours of each liked manga by content vector."""

    name = "content"

    def _find_matches(
        self,
        db: Session,
        seed_ids: Sequence[uuid.UUID],
        k: int,
    ) -> list[SeedMatches]:
        """Return the `k` nearest manga of each seed.

        Skip a seed that has no embedding.
        """
        matches: list[SeedMatches] = []
        for seed_id in seed_ids:
            embedding = get_embedding_by_manga_id(db, seed_id)
            if not embedding:
                continue

            matches.append(
                SeedMatches(
                    seed_id=seed_id,
                    match_ids=get_nearest_neighbours(db, embedding, k),
                )
            )

        return matches

    def _merge_matches(
        self,
        matches_per_seed: Sequence[SeedMatches],
        skip_ids: Collection[uuid.UUID],
        k: int,
    ) -> list[Candidate]:
        """Merge the match lists of all seeds into up to `k` candidates.

        Take one match from each seed per rank, so that each seed gets its
        best matches near the top. A match of more than one seed gets one
        reason for each seed.
        """
        candidates: dict[uuid.UUID, Candidate] = {}

        for rank in range(k):
            if len(candidates) >= k:
                break

            for seed_id, match_ids in matches_per_seed:
                if rank >= len(match_ids):
                    continue

                match_id = match_ids[rank]
                if match_id in skip_ids:
                    continue
                elif match_id in candidates:
                    candidates[match_id].reasons.append(
                        Reason(source=self.name, seed_id=seed_id)
                    )
                else:
                    candidates[match_id] = Candidate(
                        manga_id=match_id,
                        reasons=[Reason(source=self.name, seed_id=seed_id)],
                    )

        return [*candidates.values()][:k]

    def get_candidates(
        self,
        db: Session,
        query: RecommendationQuery,
        k: int,
    ) -> list[Candidate]:
        """Return up to `k` candidates, best first."""
        matches_per_seed = self._find_matches(db, query.liked_ids, k)
        return self._merge_matches(matches_per_seed, query.liked_ids, k)
