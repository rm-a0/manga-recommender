import hashlib
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from manga_recommender.pipeline.stages import embed
from manga_recommender.pipeline.stages.embed import (
    build_embedding_text,
    create_manga_embeddings,
)
from manga_recommender.pipeline.stages.export import SCHEMA

MODEL = "fake/model"
DIM = 4


class _FakeModel:
    """Stand-in for a sentence-transformer that records every text it encodes."""

    def __init__(self) -> None:
        self.encoded: list[str] = []

    def get_embedding_dimension(self) -> int:
        return DIM

    def encode(self, texts: list[str], **_: object) -> np.ndarray:
        self.encoded.extend(texts)
        return np.stack([_vector(text) for text in texts])


def _vector(text: str) -> np.ndarray:
    """Return a deterministic vector, so equal texts give equal vectors."""
    return np.frombuffer(hashlib.sha256(text.encode()).digest()[:DIM], np.uint8).astype(
        np.float32
    )


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> _FakeModel:
    fake = _FakeModel()
    monkeypatch.setattr(embed, "load_model", lambda name, device: fake)
    return fake


def _row(
    id_: str,
    *,
    title: str = "Berserk",
    description: str = "A mercenary's revenge.",
    tags: list[str] | None = None,
) -> dict[str, object]:
    return {"id": id_, "title": title, "description": description, "tags": tags}


def _write_snapshot(path: Path, rows: list[dict[str, object]]) -> None:
    pq.write_table(pa.Table.from_pylist(rows, schema=SCHEMA), path)


def _run(
    tmp_path: Path, *, model_name: str = MODEL, parquet_batch_size: int = 100
) -> Path:
    out = tmp_path / "artifacts" / "embeddings.npz"
    create_manga_embeddings(
        parquet_path=tmp_path / "manga.parquet",
        embeddings_path=out,
        parquet_batch_size=parquet_batch_size,
        encode_batch_size=8,
        model_name=model_name,
        device=None,
    )
    return out


def _artifact(path: Path) -> dict[str, np.ndarray]:
    with np.load(path) as data:
        return {key: data[key] for key in data.files}


# --- build_embedding_text ---


def test_build_embedding_text_puts_description_then_tags_then_title() -> None:
    text = build_embedding_text(
        "Berserk", "A mercenary's revenge.", ["Action", "Drama"]
    )

    assert text == (
        "Description: A mercenary's revenge.\nTags: Action, Drama\nTitle: Berserk"
    )


@pytest.mark.parametrize("tags", [None, []])
def test_build_embedding_text_leaves_out_missing_tags(tags: list[str] | None) -> None:
    assert build_embedding_text("Berserk", "Revenge.", tags) == (  # type: ignore[arg-type]
        "Description: Revenge.\nTitle: Berserk"
    )


def test_build_embedding_text_leaves_out_an_empty_description() -> None:
    assert build_embedding_text("Berserk", "", ["Action"]) == (
        "Tags: Action\nTitle: Berserk"
    )


# --- create_manga_embeddings ---


def test_create_manga_embeddings_writes_one_vector_per_row(
    model: _FakeModel, tmp_path: Path
) -> None:
    rows = [_row(str(i), description=f"Story {i}") for i in range(5)]
    _write_snapshot(tmp_path / "manga.parquet", rows)

    artifact = _artifact(_run(tmp_path, parquet_batch_size=2))

    assert artifact["ids"].tolist() == [str(i) for i in range(5)]
    assert artifact["vectors"].shape == (5, DIM)
    assert artifact["vectors"].dtype == np.float32
    assert str(artifact["model_name"]) == MODEL
    for i, row in enumerate(rows):
        text = build_embedding_text(row["title"], row["description"], row["tags"])  # type: ignore[arg-type]
        assert artifact["hashes"][i] == hashlib.sha256(text.encode()).hexdigest()
        np.testing.assert_array_equal(artifact["vectors"][i], _vector(text))


def test_create_manga_embeddings_encodes_only_new_and_changed_rows(
    model: _FakeModel, tmp_path: Path
) -> None:
    snapshot = tmp_path / "manga.parquet"
    _write_snapshot(snapshot, [_row("a"), _row("b", description="Old.")])
    _run(tmp_path)
    model.encoded.clear()

    _write_snapshot(
        snapshot,
        [_row("a"), _row("b", description="New."), _row("c", description="Added.")],
    )
    artifact = _artifact(_run(tmp_path))

    assert sorted(model.encoded) == sorted(
        [
            build_embedding_text("Berserk", "New.", []),
            build_embedding_text("Berserk", "Added.", []),
        ]
    )
    assert artifact["ids"].tolist() == ["a", "b", "c"]


def test_create_manga_embeddings_reencodes_everything_when_the_model_changes(
    model: _FakeModel, tmp_path: Path
) -> None:
    _write_snapshot(tmp_path / "manga.parquet", [_row("a"), _row("b")])
    _run(tmp_path)
    model.encoded.clear()

    _run(tmp_path, model_name="fake/other-model")

    assert len(model.encoded) == 2


def test_create_manga_embeddings_drops_rows_gone_from_the_snapshot(
    model: _FakeModel, tmp_path: Path
) -> None:
    # The artifact mirrors the snapshot, so a manga that left the export gate
    # must not survive in the vectors that `index` loads.
    snapshot = tmp_path / "manga.parquet"
    _write_snapshot(snapshot, [_row("a"), _row("b")])
    _run(tmp_path)

    _write_snapshot(snapshot, [_row("a")])
    artifact = _artifact(_run(tmp_path))

    assert artifact["ids"].tolist() == ["a"]
    assert artifact["vectors"].shape == (1, DIM)


def test_create_manga_embeddings_leaves_no_temporary_file(
    model: _FakeModel, tmp_path: Path
) -> None:
    _write_snapshot(tmp_path / "manga.parquet", [_row("a")])

    out = _run(tmp_path)

    assert [p.name for p in out.parent.iterdir()] == ["embeddings.npz"]


def test_create_manga_embeddings_rejects_an_empty_snapshot_before_loading_the_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Export writes an empty snapshot when nothing qualifies. Embed must fail
    # loudly on it, before the slow model load, and keep the previous artifact:
    # an empty artifact would let `index` wipe every stored vector.
    fake = _FakeModel()
    monkeypatch.setattr(embed, "load_model", lambda name, device: fake)
    snapshot = tmp_path / "manga.parquet"
    _write_snapshot(snapshot, [_row("a")])
    out = _run(tmp_path)
    original = out.read_bytes()

    loaded: list[str] = []
    monkeypatch.setattr(embed, "load_model", lambda name, device: loaded.append(name))
    _write_snapshot(snapshot, [])

    with pytest.raises(ValueError):
        _run(tmp_path)

    assert loaded == []
    assert out.read_bytes() == original
