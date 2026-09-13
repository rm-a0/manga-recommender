"""Load the embeddings artifact into `manga_embeddings`."""

import itertools
import os
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import structlog
from sqlalchemy.orm import Session

from manga_recommender.core.config import get_pipeline_settings
from manga_recommender.db.repositories.manga_embeddings import (
    EmbeddingValues,
    bulk_create_manga_embeddings,
    create_content_vector_index,
    delete_all_manga_embeddings,
    drop_content_vector_index,
)
from manga_recommender.db.session import session_scope

logger = structlog.get_logger(__name__)


def _load_npz(path: Path) -> list[EmbeddingValues]:
    """Read the artifact at `path` and return one row of column values per manga.

    Every row carries the artifact's model name, and the file's modification
    time in UTC as `computed_at`. Raises `ValueError` when the file is missing,
    carries no model name, or holds no vectors, so the caller never clears the
    table for an artifact it cannot replace it with.
    """
    if not path.exists():
        raise ValueError(f"{path} doesn't exist, no embeddings found")

    with np.load(path) as data:
        if "model_name" not in data.files:
            raise ValueError(f"{path} contains no 'model_name'")
        model_name = str(data["model_name"])
        ids = data["ids"]
        vectors = data["vectors"]
        if len(ids) == 0:
            raise ValueError(f"{path} holds no vectors, refusing to clear the table")

    logger.info("artifact_loaded", path=str(path), count=len(ids))

    last_modified = datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)

    return [
        EmbeddingValues(
            manga_id=uuid.UUID(id_),
            content_vector=vector,
            model_name=model_name,
            computed_at=last_modified,
        )
        for id_, vector in zip(ids, vectors, strict=True)
    ]


def store_manga_embeddings(db: Session, embeddings_path: Path, batch_size: int) -> None:
    """Replace every row in `manga_embeddings` with the artifact's vectors.

    Drops the HNSW index before the load and builds it again after, since one
    build is faster than updating the graph on every insert. `batch_size` sets
    how many rows each insert sends.

    Does not commit: the drop, the delete, every insert and the rebuild share
    the caller's transaction, so a failure part way through leaves the previous
    rows and index in place. Reads on the table wait until that transaction
    ends.
    """
    logger.info("index_started", path=str(embeddings_path), batch_size=batch_size)

    embedding_values = _load_npz(embeddings_path)
    drop_content_vector_index(db)
    deleted = delete_all_manga_embeddings(db)
    for batch in itertools.batched(embedding_values, batch_size, strict=False):
        start_time = time.monotonic()
        bulk_create_manga_embeddings(db, batch)
        logger.info(
            "batch_created",
            count=len(batch),
            elapsed_s=round(time.monotonic() - start_time, 1),
        )
    create_content_vector_index(db)

    logger.info("index_completed", deleted=deleted, inserted=len(embedding_values))


def run_index() -> None:
    """Load the embeddings artifact into `manga_embeddings` in one transaction."""
    settings = get_pipeline_settings()
    with session_scope() as session:
        store_manga_embeddings(
            db=session,
            embeddings_path=Path(settings.embeddings_path),
            batch_size=settings.db_batch_size,
        )
