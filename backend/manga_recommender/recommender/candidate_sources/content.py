import uuid

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


class ContentCandidateSource(BaseCandidateSource):
    name = "content"

    def get_candidates(
        self,
        db: Session,
        query: RecommendationQuery,
        k: int,
    ) -> list[Candidate]:
        """Return up to `k` candidates, best first."""
        candidates: dict[uuid.UUID, Candidate] = {}
        for manga_id in query.liked_ids:
            embedding = get_embedding_by_manga_id(db, manga_id)
            if not embedding:
                continue
            manga_ids = get_nearest_neighbours(db, embedding, k)

        raise NotImplementedError
