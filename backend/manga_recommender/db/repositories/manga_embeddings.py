"""Read and write the content vectors in `manga_embeddings`."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import NotRequired, TypedDict, cast

from sqlalchemy import CursorResult, delete, insert
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_embeddings import MangaEmbedding


class EmbeddingValues(TypedDict):
    """Column values for one embedding row, ready for a bulk insert."""

    manga_id: uuid.UUID
    content_vector: list[float]
    model_name: str
    computed_at: datetime
    cluster_id: NotRequired[int | None]


# --- Bulk operations ---


def delete_all_manga_embeddings(db: Session) -> int:
    """Delete every embedding row and return the number removed.

    The `index` stage clears the table before it writes the recomputed vectors.
    """
    # RETURNING sends back one id per embedded manga. Count instead.
    result = cast(CursorResult, db.execute(delete(MangaEmbedding)))
    return result.rowcount


def bulk_create_manga_embeddings(
    db: Session,
    values: Sequence[EmbeddingValues],
) -> None:
    """Insert a batch of embedding rows in one round trip.

    The caller clears the table first. There is no conflict clause, so a row
    that already exists for the same manga raises.
    """
    if not values:
        return
    db.execute(insert(MangaEmbedding), values)
