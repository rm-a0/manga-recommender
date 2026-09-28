from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

from manga_recommender.core import storage

SCHEMA = pa.schema([("id", pa.int32()), ("title", pa.string())])


def _table(ids: list[int]) -> pa.Table:
    return pa.Table.from_pylist(
        [{"id": i, "title": f"タイトル {i}"} for i in ids], schema=SCHEMA
    )


def _batches(ids: list[int], size: int):
    for start in range(0, len(ids), size):
        yield pa.RecordBatch.from_pylist(
            [{"id": i, "title": str(i)} for i in ids[start : start + size]],
            schema=SCHEMA,
        )


def _names(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def test_table_round_trips(tmp_path):
    path = tmp_path / "manga.parquet"

    storage.write_table(path, _table([1, 2, 3]))

    assert storage.read_table(path).equals(_table([1, 2, 3]))
    assert _names(tmp_path) == ["manga.parquet"]


def test_write_creates_missing_parent_directories(tmp_path):
    path = tmp_path / "artifacts" / "nested" / "community_recs.parquet"

    storage.write_table(path, _table([1]))

    assert storage.count_rows(path) == 1


def test_write_replaces_the_previous_file(tmp_path):
    path = tmp_path / "manga.parquet"
    storage.write_table(path, _table([1]))

    storage.write_table(path, _table([2, 3]))

    assert storage.read_table(path).column("id").to_pylist() == [2, 3]


def test_write_batches_streams_every_batch_and_returns_the_row_count(tmp_path):
    path = tmp_path / "manga.parquet"

    count = storage.write_batches(path, SCHEMA, _batches(list(range(5)), size=2))

    assert count == 5
    assert storage.read_table(path).column("id").to_pylist() == [0, 1, 2, 3, 4]


def test_write_batches_with_no_batches_writes_an_empty_file(tmp_path):
    path = tmp_path / "manga.parquet"

    assert storage.write_batches(path, SCHEMA, []) == 0
    assert storage.count_rows(path) == 0


def test_failed_stream_keeps_the_previous_file_and_leaves_no_temporary_file(
    tmp_path,
):
    path = tmp_path / "manga.parquet"
    storage.write_table(path, _table([1]))
    original = path.read_bytes()

    def failing_batches():
        yield from _batches([7, 8], size=1)
        raise RuntimeError("connection lost")

    with pytest.raises(RuntimeError, match="connection lost"):
        storage.write_batches(path, SCHEMA, failing_batches())

    assert path.read_bytes() == original
    assert _names(tmp_path) == ["manga.parquet"]


def test_failed_first_write_leaves_no_file(tmp_path):
    path = tmp_path / "manga.parquet"

    def failing_batches():
        raise RuntimeError("boom")
        yield

    with pytest.raises(RuntimeError):
        storage.write_batches(path, SCHEMA, failing_batches())

    assert list(tmp_path.iterdir()) == []


def test_read_batches_yields_batches_of_at_most_the_given_size(tmp_path):
    path = tmp_path / "manga.parquet"
    storage.write_table(path, _table(list(range(5))))

    sizes = [batch.num_rows for batch in storage.read_batches(path, batch_size=2)]

    assert sizes == [2, 2, 1]


def test_arrays_round_trip(tmp_path):
    path = tmp_path / "embeddings.npz"
    vectors = np.arange(6, dtype=np.float32).reshape(2, 3)

    storage.write_arrays(path, model_name="bge", ids=["a", "b"], vectors=vectors)

    arrays = storage.read_arrays(path)
    assert set(arrays) == {"model_name", "ids", "vectors"}
    assert str(arrays["model_name"]) == "bge"
    assert arrays["ids"].tolist() == ["a", "b"]
    assert np.array_equal(arrays["vectors"], vectors)
    assert _names(tmp_path) == ["embeddings.npz"]


def test_write_arrays_writes_exactly_the_given_path_without_an_npz_suffix(tmp_path):
    path = tmp_path / "embeddings"

    storage.write_arrays(path, values=np.arange(3))

    assert _names(tmp_path) == ["embeddings"]
    assert storage.read_arrays(path)["values"].tolist() == [0, 1, 2]


def test_failed_array_write_keeps_the_previous_file(tmp_path):
    path = tmp_path / "embeddings.npz"
    storage.write_arrays(path, values=np.arange(3))
    original = path.read_bytes()

    with pytest.raises(ValueError):
        storage.write_arrays(path, ragged=[[1, 2], [3]])

    assert path.read_bytes() == original
    assert _names(tmp_path) == ["embeddings.npz"]
