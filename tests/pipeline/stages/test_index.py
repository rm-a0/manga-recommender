import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from manga_recommender.db.models.manga_embeddings import MangaEmbedding
from manga_recommender.db.repositories.manga import create_manga
from manga_recommender.pipeline.stages.index import store_manga_embeddings

MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384


def _seed(db: Session, count: int) -> list[uuid.UUID]:
    """Create `count` manga and return their IDs."""
    return [
        create_manga(
            db, title=f"Manga {i}", title_english=None, description="x" * 150
        ).id
        for i in range(count)
    ]


def _write_artifact(
    path: Path, ids: list[uuid.UUID], *, model_name: str = MODEL, seed: int = 0
) -> np.ndarray:
    """Write an artifact in the shape `embed` writes, and return its vectors."""
    vectors = np.random.default_rng(seed).random((len(ids), DIM), dtype=np.float32)
    np.savez(
        path,
        model_name=model_name,
        ids=[str(id_) for id_ in ids],
        hashes=["hash"] * len(ids),
        vectors=vectors,
    )
    return vectors


def _stored(db: Session) -> dict[uuid.UUID, MangaEmbedding]:
    return {row.manga_id: row for row in db.scalars(select(MangaEmbedding))}


def test_store_manga_embeddings_writes_every_artifact_row(
    db_session: Session, tmp_path: Path
) -> None:
    ids = _seed(db_session, 5)
    path = tmp_path / "embeddings.npz"
    vectors = _write_artifact(path, ids)

    # A batch size below the row count exercises more than one insert.
    store_manga_embeddings(db_session, path, batch_size=2)

    stored = _stored(db_session)
    assert set(stored) == set(ids)
    for id_, vector in zip(ids, vectors, strict=True):
        row = stored[id_]
        assert row.model_name == MODEL
        # halfvec stores float16, so the round trip loses precision.
        np.testing.assert_allclose(row.content_vector, vector, atol=1e-3)


def test_store_manga_embeddings_replaces_the_rows_of_a_previous_run(
    db_session: Session, tmp_path: Path
) -> None:
    ids = _seed(db_session, 3)
    path = tmp_path / "embeddings.npz"
    _write_artifact(path, ids, seed=0)
    store_manga_embeddings(db_session, path, batch_size=100)

    # The second artifact drops one manga and changes every vector.
    vectors = _write_artifact(path, ids[:2], model_name="other/model", seed=1)
    store_manga_embeddings(db_session, path, batch_size=100)

    stored = _stored(db_session)
    assert set(stored) == set(ids[:2])
    assert {row.model_name for row in stored.values()} == {"other/model"}
    np.testing.assert_allclose(stored[ids[0]].content_vector, vectors[0], atol=1e-3)


def test_store_manga_embeddings_stamps_the_artifact_time_in_utc(
    db_session: Session, tmp_path: Path
) -> None:
    # The column is timezone-aware. A naive local time would be read as UTC by
    # the database and shift by the machine's offset.
    ids = _seed(db_session, 1)
    path = tmp_path / "embeddings.npz"
    _write_artifact(path, ids)

    store_manga_embeddings(db_session, path, batch_size=100)

    (row,) = _stored(db_session).values()
    expected = datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)
    assert row.computed_at == expected


def test_store_manga_embeddings_rejects_an_empty_artifact_and_keeps_the_table(
    db_session: Session, tmp_path: Path
) -> None:
    ids = _seed(db_session, 2)
    path = tmp_path / "embeddings.npz"
    _write_artifact(path, ids)
    store_manga_embeddings(db_session, path, batch_size=100)

    _write_artifact(path, [])

    with pytest.raises(ValueError, match="holds no vectors"):
        store_manga_embeddings(db_session, path, batch_size=100)

    assert set(_stored(db_session)) == set(ids)


def test_store_manga_embeddings_leaves_the_hnsw_index_in_place(
    db_session: Session, tmp_path: Path
) -> None:
    # The stage may drop the index for a faster load, but a run that forgets to
    # create it again turns every similarity query into a sequential scan.
    ids = _seed(db_session, 2)
    path = tmp_path / "embeddings.npz"
    _write_artifact(path, ids)

    store_manga_embeddings(db_session, path, batch_size=100)

    indexdef = db_session.scalar(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE indexname = 'ix_manga_embeddings_content_vector'"
        )
    )
    assert indexdef is not None
    assert "hnsw" in indexdef
    assert "halfvec_ip_ops" in indexdef


def test_store_manga_embeddings_rejects_a_missing_artifact(
    db_session: Session, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="doesn't exist"):
        store_manga_embeddings(db_session, tmp_path / "missing.npz", batch_size=100)
