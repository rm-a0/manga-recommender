"""Read and write the content vectors in `manga_embeddings`."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import NotRequired, TypedDict, cast

from sqlalchemy import CursorResult, Index, Table, delete, insert, select, text
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_embeddings import MangaEmbedding


class EmbeddingValues(TypedDict):
    """Column values for one embedding row, ready for a bulk insert."""

    manga_id: uuid.UUID
    content_vector: list[float]
    model_name: str
    computed_at: datetime
    cluster_id: NotRequired[int | None]


# --- Index maintenance ---


def _content_vector_index() -> Index:
    """Return the HNSW index that the model declares on `content_vector`.

    Reads it from the table metadata, so the drop and the rebuild use the same
    method and operator class as the migration.
    """
    # The mapper types `__table__` as `FromClause`. At runtime it is a `Table`.
    table = cast(Table, MangaEmbedding.__table__)
    return next(
        index
        for index in table.indexes
        if index.name == "ix_manga_embeddings_content_vector"
    )


def drop_content_vector_index(db: Session) -> None:
    """Drop the HNSW index on `content_vector`, if it exists.

    A bulk load into the bare table is faster than one that updates the graph
    for every row. The drop locks the table against reads until the
    transaction ends.
    """
    _content_vector_index().drop(bind=db.connection(), checkfirst=True)


def create_content_vector_index(db: Session) -> None:
    """Build the HNSW index on `content_vector` over the rows already stored.

    Turns off parallel workers for this transaction: a parallel build keeps the
    graph in a shared memory segment sized by `maintenance_work_mem`, which a
    container's small `/dev/shm` cannot hold. Raises `maintenance_work_mem` for
    this transaction only. A graph that does not fit in it still builds, but
    far slower.
    """
    db.execute(text("SET LOCAL max_parallel_maintenance_workers = 0"))
    db.execute(text("SET LOCAL maintenance_work_mem = '128MB'"))
    _content_vector_index().create(bind=db.connection())


def get_embedding_by_manga_id(
    db: Session,
    manga_id: uuid.UUID,
) -> MangaEmbedding | None:
    """Return the embedding of the manga, or None if it has no embedding."""
    return db.scalar(select(MangaEmbedding).where(MangaEmbedding.manga_id == manga_id))


def get_nearest_neighbours(
    db: Session,
    embedding: MangaEmbedding,
    n: int,
) -> Sequence[uuid.UUID]:
    """Return the ids of the `n` manga nearest to `embedding`, nearest first.

    Order by inner product, which the HNSW index supports. The vectors have
    unit length, so this order is the cosine order. An HNSW scan returns at most
    `hnsw.ef_search` rows, so set it to at least `n` for this transaction.
    """
    db.execute(
        text("SELECT set_config('hnsw.ef_search', :ef, true)"),
        {"ef": str(max(n, 40))},
    )
    return db.scalars(
        select(MangaEmbedding.manga_id)
        .where(MangaEmbedding.id != embedding.id)
        .order_by(
            MangaEmbedding.content_vector.max_inner_product(embedding.content_vector)
        )
        .limit(n)
    ).all()


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
