from collections.abc import Sequence
from datetime import datetime
from typing import TypedDict, cast
import uuid

from manga_recommender.db.models.manga_embeddings import MangaEmbedding
from sqlalchemy import CursorResult, delete, insert
from sqlalchemy.orm import Session


class EmbeddingValues(TypedDict):
    manga_id: uuid.UUID
    content_vector: list[float]
    model_name: str
    computed_at: datetime
    cluster_id: int | None


# --- Bulk operations ---


def delete_all_manga_embeddings(db: Session) -> int:
    result = cast(CursorResult, db.execute(delete(MangaEmbedding)))
    return result.rowcount


def bulk_update_or_create_manga_embedding(
    db: Session,
    values: Sequence[EmbeddingValues],
) -> None:
    if not values:
        return
    db.execute(insert(MangaEmbedding), values)
