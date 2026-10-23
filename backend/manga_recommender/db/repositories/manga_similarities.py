"""Read and write the scored neighbour edges in `manga_similarities`."""

import uuid
from collections.abc import Sequence
from typing import TypedDict, cast

from sqlalchemy import CursorResult, delete, insert
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_similarities import (
    MangaSimilarity,
    SimilarityMethod,
)


class SimilarityValues(TypedDict):
    """Column values for one bulk-inserted similarity edge."""

    manga_id: uuid.UUID
    method: SimilarityMethod
    similar_manga_id: uuid.UUID
    score: float


def create_manga_similarity(
    db: Session,
    *,
    manga_id: uuid.UUID,
    method: SimilarityMethod,
    similar_manga_id: uuid.UUID,
    score: float,
) -> MangaSimilarity:
    """Create and persist a new similarity edge."""
    db_manga_similarity = MangaSimilarity(
        manga_id=manga_id,
        method=method,
        similar_manga_id=similar_manga_id,
        score=score,
    )
    db.add(db_manga_similarity)
    db.flush()
    return db_manga_similarity


# --- Bulk operations ---


def delete_manga_similarities_by_method(db: Session, method: SimilarityMethod) -> int:
    """Delete every edge that `method` produced and return the number removed.

    Edges from other methods stay, so each stage can rebuild only its own rows.
    """
    result = cast(
        CursorResult,
        db.execute(delete(MangaSimilarity).where(MangaSimilarity.method == method)),
    )
    return result.rowcount


def bulk_create_manga_similarities(
    db: Session,
    values: Sequence[SimilarityValues],
) -> None:
    """Insert a batch of similarity edges.

    The caller deletes the method's edges first. There is no conflict clause, so
    an edge that already exists for the same manga pair and method raises.
    """
    if not values:
        return
    db.execute(insert(MangaSimilarity), values)
