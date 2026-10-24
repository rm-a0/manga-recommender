"""Read and write the scored neighbour edges in `manga_similarities`."""

import uuid
from collections.abc import Sequence
from typing import TypedDict, cast

from sqlalchemy import CursorResult, delete, insert, select
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga import Manga
from manga_recommender.db.models.manga_similarities import (
    MangaSimilarity,
    SimilarityMethod,
)
from manga_recommender.db.repositories.manga import MangaFilters, filter_clauses


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


def get_similar_manga_ids(
    db: Session,
    manga_id: uuid.UUID,
    method: SimilarityMethod,
    filters: MangaFilters,
    n: int,
) -> Sequence[uuid.UUID]:
    """Return up to `n` neighbours of one manga from `method`, best first.

    Return only the neighbours that pass `filters`. `similar_manga_id` breaks a
    tie, so two neighbours with the same score keep one order.
    """
    return db.scalars(
        select(MangaSimilarity.similar_manga_id)
        .join(Manga, Manga.id == MangaSimilarity.similar_manga_id)
        .where(MangaSimilarity.manga_id == manga_id)
        .where(MangaSimilarity.method == method)
        .where(*filter_clauses(filters))
        .order_by(MangaSimilarity.score.desc(), MangaSimilarity.similar_manga_id)
        .limit(n)
    ).all()


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
