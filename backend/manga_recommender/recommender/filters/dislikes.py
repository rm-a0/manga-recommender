"""Drop the candidates that sit close to a manga the reader disliked."""

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from manga_recommender.db.repositories.manga_embeddings import (
    get_embedding_by_manga_id,
    get_manga_ids_near,
)
from manga_recommender.recommender.base import Candidate, RecommendationQuery
from manga_recommender.recommender.filters.common import drop_ids


def drop_near_dislikes(
    db: Session,
    query: RecommendationQuery,
    candidates: Sequence[Candidate],
) -> list[Candidate]:
    """Return the candidates that no disliked manga sits close to.

    Close means a cosine similarity at or above `query.dislike_similarity_cutoff`.
    At the default, only a near duplicate drops, such as a sequel or a
    re-release. Skip a disliked manga that has no embedding.
    """
    if not query.disliked_ids or not candidates:
        return list(candidates)

    exclude_ids: set[uuid.UUID] = set()
    candidate_ids = [c.manga_id for c in candidates]
    for disliked_id in query.disliked_ids:
        embedding = get_embedding_by_manga_id(db, disliked_id)
        if not embedding:
            continue

        exclude_ids.update(
            get_manga_ids_near(
                db,
                embedding,
                candidate_ids,
                query.dislike_similarity_cutoff,
            )
        )
    return drop_ids(candidates, exclude_ids)
